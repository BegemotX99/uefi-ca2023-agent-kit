"""Build a bootable MBR/FAT32 image and validate the selected release assets."""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import secrets
from pathlib import Path
import struct

MIB=1024*1024
MIN_DISK=256*MIB
MAX_DISK=512*1024*MIB
SECTOR=512
START=2048


def digest(data):return sha256(data).hexdigest()


def load_assets(root):
    root=Path(root)
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if {b['id'] for b in manifest['boards']}!={'f8','mr9s','h9s001','h9s002'}:
        raise ValueError('Unexpected embedded motherboard catalog')
    for item in manifest['files']:
        path=(root/item['path']).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path.read_bytes())!=item['sha256']:
            raise ValueError('Embedded asset missing or altered: '+item['path'])
    for board in manifest['boards']:
        for kind in ('modified','original'):
            p=root/board[kind]
            if p.stat().st_size!=16*MIB:raise ValueError('Expected full 16 MiB image')
    return manifest


def selected_files(root,manifest,board_id):
    root=Path(root)
    board=next((b for b in manifest['boards'] if b['id']==board_id),None)
    if board is None:raise ValueError('Choose one included motherboard')
    files={name:(root/source).read_bytes() for name,source in manifest['dos_files'].items()}
    files['BIOS.BIN']=(root/board['modified']).read_bytes()
    files['FACTORY.BIN']=(root/board['original']).read_bytes()
    files['BOARD.CFG']=(board['id']+'\r\n').encode('ascii')
    files['README.TXT']=(
        'PRISM SPI FLASH USB\r\nBoard: '+board['name']+'\r\n'
        'BIOS.BIN: full 16 MiB CA 2023-modified firmware.\r\n'
        'FACTORY.BIN: exact original reference, not a backup of your board.\r\n'
        'Select the Legacy/CSM USB boot entry. FreeDOS is not UEFI-native.\r\n'
        '1 backs up the entire 16 MiB SPI chip to a new BACKnnnn.BIN.\r\n'
        '2 writes the entire selected BIOS.BIN and reads all 16 MiB back.\r\n'
        'Writes require typed FLASH confirmation and stop on any tool error.\r\n'
        'The PC must match the selected motherboard and revision.\r\n'
        'SPI locks and unsupported chips are not bypassed. See FLASH.LOG.\r\n'
        'Prebuilt images use the author\'s Secure Boot key. Build with your\r\n'
        'own key if you want to manage Secure Boot yourself.\r\n'
        'FreeDOS and program sources/notices: SOURCE.ZIP.\r\n').encode('ascii')
    return board,files


@dataclass(frozen=True)
class Plan:
    size:int
    partition_sectors:int
    spc:int
    fat_sectors:int
    clusters:int
    @property
    def fat_offset(self):return (START+32)*SECTOR
    @property
    def data_offset(self):return (START+32+2*self.fat_sectors)*SECTOR


def geometry(size):
    if not MIN_DISK<=size<=MAX_DISK or size%512:
        raise ValueError('Supported USB capacity: 256 MiB to 512 GiB, 512-byte sectors')
    total=size//512-START-2048
    spc=4 if size<=512*MIB else 8 if size<=8*1024*MIB else 64
    fat=((total//spc+2)*4+511)//512
    clusters=(total-32-2*fat)//spc
    if not 65525<=clusters<0x0ffffff5 or fat*128<clusters+2:
        raise ValueError('Invalid FAT32 geometry')
    return Plan(size,total,spc,fat,clusters)


def short_name(name):
    parts=name.split('.')
    if len(parts)>2 or not 1<=len(parts[0])<=8 or len(parts[-1])>8:
        raise ValueError('Not a DOS 8.3 name: '+name)
    stem=parts[0];extension=parts[1] if len(parts)==2 else ''
    if len(extension)>3 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in stem+extension):
        raise ValueError('Unsafe DOS filename: '+name)
    return (stem.ljust(8)+extension.ljust(3)).encode('ascii')


def make_sparse(stream):
    import os
    if os.name=='nt':
        import ctypes,msvcrt
        returned=ctypes.c_ulong()
        fn=ctypes.windll.kernel32.DeviceIoControl
        fn.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.c_void_p]
        if not fn(msvcrt.get_osfhandle(stream.fileno()),0x900c4,None,0,None,0,ctypes.byref(returned),None):
            raise OSError('Temporary image folder must support sparse files (NTFS recommended)')


def build_image(path,size,files,mbr_code,vbr_code,progress=lambda message:None):
    plan=geometry(size)
    if len(mbr_code)!=440 or len(vbr_code)!=512 or vbr_code[510:]!=b'\x55\xaa':
        raise ValueError('Invalid verified FreeDOS boot code')
    if not {'KERNEL.SYS','COMMAND.COM','AUTOEXEC.BAT','FDCONFIG.SYS','PRISM.EXE','BIOS.BIN','BOARD.CFG'}<=set(files):
        raise ValueError('Incomplete boot/flash payload')
    if len(files['BIOS.BIN'])!=16*MIB:raise ValueError('BIOS image must be full 16 MiB')
    cluster_bytes=plan.spc*512
    if (len(files)+1)*32>cluster_bytes:raise ValueError('Root directory exceeds its allocation')
    fat=bytearray(plan.fat_sectors*512)
    struct.pack_into('<III',fat,0,0x0ffffff8,0x0fffffff,0x0fffffff)
    next_cluster=3;entries=bytearray(cluster_bytes);entries[:11]=b'PRISMFLASH ';entries[11]=8
    allocations=[]
    now=datetime.now();date=((now.year-1980)<<9)|(now.month<<5)|now.day;time=(now.hour<<11)|(now.minute<<5)|(now.second//2)
    for index,(name,content) in enumerate(files.items(),1):
        count=max(1,(len(content)+cluster_bytes-1)//cluster_bytes)
        if next_cluster+count>plan.clusters+2:raise ValueError('USB payload exceeds volume capacity')
        for cluster in range(next_cluster,next_cluster+count):
            struct.pack_into('<I',fat,cluster*4,cluster+1 if cluster+1<next_cluster+count else 0x0fffffff)
        entry=bytearray(32);entry[:11]=short_name(name);entry[11]=0x20
        struct.pack_into('<HHHH',entry,20,next_cluster>>16,time,date,next_cluster&0xffff)
        # FAT directory layout: high cluster at 20, time/date at 22/24,
        # low cluster at 26, size at 28.
        struct.pack_into('<H',entry,26,next_cluster&0xffff);struct.pack_into('<I',entry,28,len(content))
        entries[index*32:(index+1)*32]=entry
        allocations.append((name,next_cluster,content));next_cluster+=count
    free=plan.clusters-(next_cluster-2)
    if free*cluster_bytes<64*MIB:raise ValueError('Need 64 MiB free for backup, preflight and readback')
    disk_signature=secrets.randbits(32) or 1
    mbr=bytearray(512);mbr[:440]=mbr_code
    struct.pack_into('<I',mbr,440,disk_signature)
    struct.pack_into('<B3sB3sII',mbr,446,0x80,b'\x20\x21\x00',0x0c,b'\xfe\xff\xff',START,plan.partition_sectors)
    mbr[510:]=b'\x55\xaa'
    boot=bytearray(vbr_code);boot[3:11]=b'PRISMUSB'
    struct.pack_into('<HBHBHHBHHHII',boot,11,512,plan.spc,32,2,0,0,0xf8,0,63,255,START,plan.partition_sectors)
    struct.pack_into('<IHHIHH',boot,36,plan.fat_sectors,0,0,2,1,6)
    boot[52:64]=bytes(12);boot[64:67]=bytes([0x80,0,0x29]);struct.pack_into('<I',boot,67,disk_signature)
    boot[71:82]=b'PRISMFLASH ';boot[82:90]=b'FAT32   '
    info=bytearray(512);struct.pack_into('<I',info,0,0x41615252);struct.pack_into('<III',info,484,0x61417272,free,next_cluster);info[508:]=b'\x00\x00\x55\xaa'
    progress('Build active MBR partition, FAT32 filesystem and FreeDOS boot sectors.')
    path=Path(path)
    with path.open('x+b') as stream:
        make_sparse(stream);stream.truncate(size)
        stream.write(mbr);stream.seek(START*512);stream.write(boot);stream.write(info)
        stream.seek((START+6)*512);stream.write(boot);stream.write(info)
        stream.seek(plan.fat_offset);stream.write(fat);stream.write(fat)
        stream.seek(plan.data_offset);stream.write(entries)
        for name,cluster,content in allocations:
            stream.seek(plan.data_offset+(cluster-2)*cluster_bytes);stream.write(content)
            progress('Add '+name+' ('+str(len(content))+' bytes).')
        stream.flush()
    end=plan.data_offset+(next_cluster-2)*cluster_bytes
    with path.open('rb') as stream:
        if stream.read(512)!=mbr:raise ValueError('MBR image readback failed')
        for name,cluster,content in allocations:
            stream.seek(plan.data_offset+(cluster-2)*cluster_bytes)
            if digest(stream.read(len(content)))!=digest(content):raise ValueError('Image file readback failed: '+name)
    return dict(size=size,used_end=end,disk_signature=disk_signature,board=files['BOARD.CFG'].decode().strip(),
                files={name:dict(size=len(data),sha256=digest(data)) for name,data in files.items()},
                partition_start=START*512,partition_sectors=plan.partition_sectors,spc=plan.spc)
