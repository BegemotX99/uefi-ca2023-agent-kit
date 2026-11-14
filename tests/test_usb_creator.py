"""File-only tests: these never enumerate, open or write a physical disk."""
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'usb_creator'))
from core import geometry,short_name,build_image,MIB,make_sparse
from windows_disk import blocked_reason,require_same,write_image,prepare_physical_usb

class UsbTests(unittest.TestCase):
    def test_capacity_boundaries(self):
        for size in (256*MIB,512*MIB,8*1024*MIB,512*1024*MIB):
            p=geometry(size)
            self.assertGreaterEqual(p.clusters,65525)
            self.assertGreaterEqual(p.fat_sectors*128,p.clusters+2)
        for size in (0,255*MIB,256*MIB+1,513*1024*MIB):
            with self.assertRaises(ValueError):geometry(size)

    def test_names(self):
        self.assertEqual(short_name('BIOS.BIN'),b'BIOS    BIN')
        for name in ('../BIOS','BIOS.BIN.EXE','TOOLONGNAME.BIN','a.bin','A.TOOLONG','A/B'):
            with self.assertRaises(ValueError):short_name(name)

    def test_target_guards(self):
        d=dict(number=9,serial='AB123',unique_id='id',size=256*MIB,sector=512,bus='USB',model='Test',letters=['F'])
        self.assertIsNone(blocked_reason(d,'C:/tool.exe'))
        for changed in (dict(bus='SATA'),dict(is_boot=True),dict(is_system=True),dict(readonly=True),dict(offline=True),dict(sector=4096),dict(serial='0000')):
            self.assertIsNotNone(blocked_reason(dict(d,**changed),'C:/tool.exe'))
        self.assertIsNotNone(blocked_reason(d,'F:/tool.exe'))
        with self.assertRaises(ValueError):require_same(d,dict(d,serial='OTHER'),'C:/tool.exe')
        with self.assertRaises(ValueError):require_same(d,dict(d,is_system=True),'C:/tool.exe')

    def test_file_writer_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            image=Path(directory)/'image';target=Path(directory)/'target'
            size=4*MIB;used=2*MIB
            with image.open('w+b') as f:
                make_sparse(f);f.truncate(size);f.write(b'M'*512);f.seek(512);f.write(b'P'*(used-512))
            with target.open('w+b') as f:
                make_sparse(f);f.truncate(size);f.seek(size-MIB);f.write(b'X'*MIB)
                write_image(f,image,used,size)
                f.seek(0);self.assertEqual(f.read(used),image.read_bytes()[:used])
                f.seek(size-MIB);self.assertEqual(f.read(),bytes(MIB))
            class BadRead(io.BytesIO):
                def read(self,n=-1):return b'X'*n
            with self.assertRaisesRegex(OSError,'readback mismatch'):
                write_image(BadRead(bytes(size)),image,used,size)

    @unittest.skipUnless(sys.platform=='win32','Windows handle guards')
    def test_open_handle_identity_before_mutation(self):
        disk=dict(number=9,serial='AB123',unique_id='id',size=256*MIB,sector=512,bus='USB',model='Test',letters=[],volumes=[])
        class Fake:
            def __init__(self,*args):self.calls=[];self.closed=False
            def ioctl(self,code,data=b'',size=0):
                self.calls.append(code)
                if code==0x7405c:return struct.pack('<Q',disk['size'])
                if code==0x2d1080:return struct.pack('<III',7,9,0)
                if code==0x2d1400:
                    descriptor=bytearray(128);struct.pack_into('<I',descriptor,24,64);struct.pack_into('<I',descriptor,28,7);descriptor[64:70]=b'AB123\0';return bytes(descriptor)
                return b''
            def close(self):self.closed=True
        for matching in (False,True):
            handle=Fake()
            expected=dict(disk) if matching else dict(disk,serial='CHANGED')
            with patch('ctypes.windll.shell32.IsUserAnAdmin',return_value=1),patch('windows_disk.enumerate_usb',return_value=[disk]),patch('windows_disk.RawHandle',return_value=handle),patch('windows_disk.write_image') as writer:
                if matching:
                    prepare_physical_usb(expected,'file-only-test',123)
                    self.assertIn(0x7c100,handle.calls);writer.assert_called_once();self.assertTrue(handle.closed)
                else:
                    with self.assertRaises(ValueError):prepare_physical_usb(expected,'file-only-test',123)
                    self.assertNotIn(0x7c100,handle.calls);writer.assert_not_called()
        # A stale inventory must also fail on the actual opened device descriptor.
        handle=Fake();disk2=dict(disk,serial='OTHER')
        with patch('ctypes.windll.shell32.IsUserAnAdmin',return_value=1),patch('windows_disk.enumerate_usb',return_value=[disk2]),patch('windows_disk.RawHandle',return_value=handle),patch('windows_disk.write_image') as writer:
            with self.assertRaisesRegex(ValueError,'Open device handle'):prepare_physical_usb(disk2,'file-only-test',123)
            self.assertNotIn(0x7c100,handle.calls);writer.assert_not_called();self.assertTrue(handle.closed)

    def test_mbr_fat_and_directory(self):
        files={name:b'test' for name in ('KERNEL.SYS','COMMAND.COM','AUTOEXEC.BAT','FDCONFIG.SYS','PRISM.EXE','BOARD.CFG')}
        files['BIOS.BIN']=b'B'*(16*MIB)
        vbr=bytearray(512);vbr[510:]=b'\x55\xaa'
        with tempfile.TemporaryDirectory() as directory:
            image=Path(directory)/'usb.img'
            meta=build_image(image,256*MIB,files,bytes(440),vbr)
            p=geometry(256*MIB)
            with image.open('rb') as f:
                m=f.read(512);self.assertEqual(m[446],0x80);self.assertEqual(m[450],0x0c)
                signature=struct.unpack_from('<I',m,440)[0];self.assertNotEqual(signature,0)
                f.seek(2048*512+67);self.assertEqual(struct.unpack('<I',f.read(4))[0],signature)
                self.assertEqual(struct.unpack_from('<I',m,454)[0],2048)
                f.seek(p.fat_offset);fat1=f.read(p.fat_sectors*512);self.assertEqual(fat1,f.read(len(fat1)))
                f.seek(p.data_offset);directory=f.read(p.spc*512)
                for i,(name,data) in enumerate(files.items(),1):
                    entry=directory[i*32:(i+1)*32]
                    self.assertEqual(entry[:11],short_name(name))
                    cluster=(struct.unpack_from('<H',entry,20)[0]<<16)|struct.unpack_from('<H',entry,26)[0]
                    self.assertEqual(struct.unpack_from('<I',entry,28)[0],len(data))
                    f.seek(p.data_offset+(cluster-2)*p.spc*512);self.assertEqual(f.read(len(data)),data)
            self.assertEqual(meta['size'],256*MIB)
            with self.assertRaises(FileExistsError):build_image(image,256*MIB,files,bytes(440),vbr)

if __name__=='__main__':unittest.main()
