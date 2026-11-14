"""Windows USB inventory and guarded raw-device writing. No writes on import."""
import base64
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

FLAGS=getattr(subprocess,'CREATE_NO_WINDOW',0)


def powershell(script):
    executable=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    encoded=base64.b64encode(script.encode('utf-16le')).decode()
    result=subprocess.run([str(executable),'-NoProfile','-NonInteractive','-EncodedCommand',encoded],
        check=True,capture_output=True,timeout=45,creationflags=FLAGS)
    return result.stdout.decode('utf-8-sig',errors='replace').strip()


def enumerate_usb():
    script=r'''
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$rows=@(Get-Disk | Where-Object {$_.BusType -eq 'USB'} | ForEach-Object {
 $d=$_; $p=@(Get-Partition -DiskNumber $d.Number -ErrorAction SilentlyContinue)
 $paths=@($p | ForEach-Object {$_.AccessPaths} | Where-Object {$_ -match 'Volume\{'} | Select-Object -Unique)
 [pscustomobject]@{number=[int]$d.Number;model=[string]$d.FriendlyName;serial=([string]$d.SerialNumber).Trim();unique_id=[string]$d.UniqueId;
 size=[long]$d.Size;sector=[int]$d.LogicalSectorSize;bus='USB';is_boot=[bool]$d.IsBoot;is_system=[bool]$d.IsSystem;
 readonly=[bool]$d.IsReadOnly;offline=[bool]$d.IsOffline;letters=@($p | Where-Object DriveLetter | ForEach-Object {[string]$_.DriveLetter});volumes=$paths}
})
ConvertTo-Json -InputObject $rows -Depth 5 -Compress
'''
    data=json.loads(powershell(script) or '[]')
    if not isinstance(data,list):raise ValueError('Unexpected Windows disk inventory')
    return data


def identity(disk):
    return tuple(disk.get(k) for k in ('number','serial','unique_id','size','sector','bus','model'))


def blocked_reason(disk,app_path=None):
    if disk.get('bus')!='USB':return 'Not a USB device'
    if disk.get('is_boot') or disk.get('is_system'):return 'Windows boot/system disk'
    if disk.get('readonly') or disk.get('offline'):return 'Read-only or offline disk'
    if disk.get('sector')!=512:return 'Only 512-byte logical sectors are supported'
    if not 256*1024**2<=disk.get('size',0)<=512*1024**3:return 'Capacity must be 256 MiB to 512 GiB'
    serial=disk.get('serial','').strip()
    if len(serial)<3 or not set(serial)-set('0 -'):return 'No usable USB serial number; identity cannot be guarded'
    path=str(app_path or sys.executable)
    if len(path)>1 and path[1]==':' and path[0].upper() in [str(x).upper() for x in disk.get('letters',[])]:
        return 'This drive contains the running application; run it from another drive'
    return None


def require_same(expected,current,app_path=None):
    if identity(expected)!=identity(current):raise ValueError('USB identity changed. Refresh the drive list and select it again.')
    reason=blocked_reason(current,app_path)
    if reason:raise ValueError(reason)


def write_image(target,image,used_end,size,progress=lambda message:None):
    """Target is a seek/read/write/flush object; shared with file-only tests."""
    if not 512<used_end<size-1024*1024 or used_end%512:raise ValueError('Invalid prepared image range')
    progress('Clear stale backup partition metadata at the disk tail.')
    target.seek(size-1024*1024);target.write(bytes(1024*1024))
    progress('Write FreeDOS, filesystem metadata and selected firmware files.')
    with Path(image).open('rb') as source:
        source.seek(512);target.seek(512);remaining=used_end-512
        while remaining:
            chunk=source.read(min(4*1024*1024,remaining))
            if not chunk:raise OSError('Prepared image was truncated')
            count=target.write(chunk)
            if count is not None and count!=len(chunk):raise OSError('Incomplete USB write')
            remaining-=len(chunk)
        source.seek(0);target.seek(0);target.write(source.read(512))
        target.flush()
        progress('Read back MBR, FreeDOS boot sectors, FATs and every copied file.')
        source.seek(0);target.seek(0);remaining=used_end
        while remaining:
            count=min(4*1024*1024,remaining)
            if target.read(count)!=source.read(count):raise OSError('USB raw readback mismatch')
            remaining-=count
    target.seek(size-1024*1024)
    if target.read(1024*1024)!=bytes(1024*1024):raise OSError('USB tail cleanup readback mismatch')


class RawHandle:
    def __init__(self,path):
        import ctypes
        self.c=ctypes
        self.k=ctypes.WinDLL('kernel32',use_last_error=True)
        self.k.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
        self.k.CreateFileW.restype=ctypes.c_void_p
        self.k.DeviceIoControl.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.c_void_p]
        self.k.SetFilePointerEx.argtypes=[ctypes.c_void_p,ctypes.c_longlong,ctypes.c_void_p,ctypes.c_ulong]
        self.k.ReadFile.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.c_void_p]
        self.k.WriteFile.argtypes=self.k.ReadFile.argtypes
        self.k.FlushFileBuffers.argtypes=[ctypes.c_void_p];self.k.CloseHandle.argtypes=[ctypes.c_void_p]
        self.handle=self.k.CreateFileW(path,0xc0000000,3,None,3,0x80000000,None)
        if self.handle in (None,ctypes.c_void_p(-1).value):raise ctypes.WinError(ctypes.get_last_error())
    def ioctl(self,code,data=b'',size=0):
        c=self.c;n=c.c_ulong();out=c.create_string_buffer(size) if size else None;inp=c.create_string_buffer(data) if data else None
        if not self.k.DeviceIoControl(self.handle,code,inp,len(data),out,size,c.byref(n),None):raise c.WinError(c.get_last_error())
        return out.raw[:n.value] if out is not None else b''
    def seek(self,offset):
        if offset<0 or not self.k.SetFilePointerEx(self.handle,offset,None,0):raise self.c.WinError(self.c.get_last_error())
    def read(self,size):
        c=self.c;buf=c.create_string_buffer(size);n=c.c_ulong()
        if not self.k.ReadFile(self.handle,buf,size,c.byref(n),None):raise c.WinError(c.get_last_error())
        return buf.raw[:n.value]
    def write(self,data):
        c=self.c;buf=c.create_string_buffer(data);n=c.c_ulong()
        if not self.k.WriteFile(self.handle,buf,len(data),c.byref(n),None) or n.value!=len(data):raise c.WinError(c.get_last_error())
        return n.value
    def flush(self):
        if not self.k.FlushFileBuffers(self.handle):raise self.c.WinError(self.c.get_last_error())
    def close(self):
        if self.handle:self.k.CloseHandle(self.handle);self.handle=None


def prepare_physical_usb(expected,image,used_end,progress=lambda message:None):
    """Called only after the GUI's explicit erase confirmation. Never at startup."""
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():raise PermissionError('Run Prism as administrator to prepare a USB')
    current=next((d for d in enumerate_usb() if d['number']==expected['number']),None)
    if current is None:raise ValueError('Selected USB was disconnected')
    require_same(expected,current)
    if current.get('letters') and not current.get('volumes'):
        raise ValueError('Cannot identify mounted volumes to lock; no disk write is permitted')
    disks=enumerate_usb()
    if sum(d['serial']==expected['serial'] for d in disks)!=1:raise ValueError('Ambiguous USB serial number')
    handles=[];disk=None
    try:
        for path in current.get('volumes',[]):
            volume=RawHandle(path.rstrip('\\'));handles.append(volume)
            volume.ioctl(0x90018);volume.ioctl(0x90020)
        disk=RawHandle('\\\\.\\PhysicalDrive'+str(int(current['number'])))
        length=struct.unpack('<Q',disk.ioctl(0x7405c,size=8))[0]
        device=struct.unpack('<III',disk.ioctl(0x2d1080,size=12))[1]
        descriptor=disk.ioctl(0x2d1400,bytes(12),4096)
        serial_offset=struct.unpack_from('<I',descriptor,24)[0]
        bus=struct.unpack_from('<I',descriptor,28)[0]
        serial=descriptor[serial_offset:].split(b'\0',1)[0].decode('ascii',errors='replace').strip() if 0<serial_offset<len(descriptor) else ''
        if length!=current['size'] or device!=current['number'] or bus!=7 or serial.casefold()!=current['serial'].casefold():
            raise ValueError('Open device handle does not match the selected USB identity')
        progress('Identity rechecked on the open USB handle; old volumes locked and dismounted.')
        disk.ioctl(0x7c100) # IOCTL_DISK_DELETE_DRIVE_LAYOUT, only after all guards.
        write_image(disk,image,used_end,current['size'],progress)
        disk.ioctl(0x70140) # IOCTL_DISK_UPDATE_PROPERTIES
    finally:
        if disk:disk.close()
        for handle in reversed(handles):handle.close()
    progress('USB raw readback verified. Reconnect the USB if Windows has not assigned a letter.')
