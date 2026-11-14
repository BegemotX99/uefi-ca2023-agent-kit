"""Build a Windows x64 onedir application, then place the entire folder in one ZIP."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work-dir',required=True,type=Path)
    p.add_argument('--openssl-dir',required=True,type=Path)
    p.add_argument('--openssl-license',required=True,type=Path)
    p.add_argument('--uefiextract',required=True,type=Path)
    p.add_argument('--certificates-dir',required=True,type=Path)
    args=p.parse_args()
    work=args.work_dir.resolve();work.mkdir(parents=True,exist_ok=True)
    resources=work/'resources';resources.mkdir(exist_ok=True)
    def copy(source,name):
        dest=resources/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    scripts=ROOT/'skills/uefi-ca2023/scripts'
    sys.path.insert(0,str(scripts))
    import firmware_formats as f
    for name in ('openssl.exe','libcrypto-3-x64.dll','libssl-3-x64.dll'):
        copy(args.openssl_dir/name,'tools/OpenSSL/'+name)
    copy(args.uefiextract,'tools/UEFIExtract.exe')
    for name in ('enrollment-families.json','reviewed-images.json','microsoft-certificates.json'):
        copy(ROOT/'skills/uefi-ca2023/references'/name,'references/'+name)
    expected={sha for values in f.CERTIFICATES.values() for sha in values.values()}
    found=set()
    for source in args.certificates_dir.glob('*.der'):
        sha=f.digest(source.read_bytes())
        if sha in expected:
            copy(source,'microsoft-certificates/'+source.name);found.add(sha)
    if found!=expected:raise ValueError('The four pinned Microsoft certificates are required')
    copy(ROOT/'LICENSE','licenses/PROJECT-MIT.txt')
    copy(Path(sys.base_prefix)/'LICENSE.txt','licenses/PYTHON.txt')
    copy(args.openssl_license,'licenses/OPENSSL.txt')
    for package in ('cryptography','pyinstaller'):
        dist=importlib.metadata.distribution(package)
        for source in dist.files:
            if '.dist-info/licenses/' in str(source).replace('\\','/'):
                file=Path(dist.locate_file(source))
                if file.is_file():copy(file,'licenses/'+package+'/'+file.name)
    licenses={
      'UEFIEXTRACT-BSD.txt':'https://raw.githubusercontent.com/LongSoft/UEFITool/A76/LICENSE.md',
      'TCL-8.6.12.txt':'https://raw.githubusercontent.com/tcltk/tcl/core-8-6-12/license.terms',
      'TK-8.6.12.txt':'https://raw.githubusercontent.com/tcltk/tk/core-8-6-12/license.terms',
      'MICROSOFT-OBJECTS.txt':'https://raw.githubusercontent.com/microsoft/secureboot_objects/3d762aecbaecd12402efd21ba89c8c7bd40da4bd/License.txt',
    }
    for name,url in licenses.items():
        data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'uefi-ca2023-agent-kit'}),timeout=30).read()
        (resources/'licenses'/name).write_bytes(data)
    versions=dict(python=sys.version.split()[0],cryptography=importlib.metadata.version('cryptography'),
                  pyinstaller=importlib.metadata.version('pyinstaller'),
                  openssl=subprocess.check_output([str(args.openssl_dir/'openssl.exe'),'version'],text=True).strip(),
                  uefiextract=subprocess.check_output([str(args.uefiextract),'--version'],text=True).strip())
    manifest=dict(versions=versions,files=[dict(path=file.relative_to(resources).as_posix(),sha256=f.digest(file.read_bytes()))
        for file in sorted(resources.rglob('*')) if file.is_file() and file.name!='DEPENDENCIES.json'])
    (resources/'DEPENDENCIES.json').write_text(json.dumps(manifest,indent=2)+'\n')
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--onedir','--windowed','--noupx',
       '--name','UEFI-CA2023-AutoDetect','--distpath',str(work/'dist'),'--workpath',str(work/'build'),
       '--specpath',str(work/'spec'),'--paths',str(scripts),'--paths',str(ROOT/'windows'),
       '--collect-all','cryptography','--add-data',str(resources)+os.pathsep+'.',str(ROOT/'windows/patcher_gui.py')]
    subprocess.run(command,check=True)
    app=work/'dist/UEFI-CA2023-AutoDetect'
    # Runtime libraries must remain beside the EXE in its onedir distribution.
    for name in ('vcruntime140.dll','vcruntime140_1.dll'):
        if not (app/'_internal'/name).is_file():shutil.copyfile(Path(sys.base_prefix)/name,app/'_internal'/name)
    shutil.copyfile(ROOT/'windows/README.txt',app/'START-HERE.txt')
    shutil.copyfile(ROOT/'LICENSE',app/'LICENSE-PROJECT.txt')
    (app/'BUILD-VERSIONS.json').write_text(json.dumps(versions,indent=2)+'\n')
    # Fail the build if any non-system PE import is absent from the bundle.
    import pefile
    native=[file for file in app.rglob('*') if file.is_file() and file.suffix.lower() in ('.exe','.dll','.pyd')]
    shipped={file.name.lower() for file in native}
    missing=[]
    for file in native:
        pe=pefile.PE(str(file),fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
        for imported in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
            name=imported.dll.decode().lower()
            if name not in shipped and not name.startswith(('api-ms-win-','ext-ms-win-')) and not (Path(os.environ['SystemRoot'])/'System32'/name).exists():
                missing.append((file.name,name))
        pe.close()
    if missing:raise ValueError('Unresolved native imports: '+repr(missing))
    (app/'SHA256SUMS.txt').write_text(''.join(f'{f.digest(file.read_bytes())}  {file.relative_to(app).as_posix()}\n'
        for file in sorted(app.rglob('*')) if file.is_file() and file.name!='SHA256SUMS.txt'))
    archive=work/'UEFI-CA2023-AutoDetect-Windows-x64-Portable.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in app.rglob('*'):
            if file.is_file():z.write(file,file.relative_to(app.parent))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any(name.lower().endswith(('.pem','.key','.pfx','.p12','.dpapi','.bin','.rom')) for name in z.namelist())
    print(json.dumps(dict(archive=str(archive),size=archive.stat().st_size,sha256=f.digest(archive.read_bytes()),versions=versions),indent=2))


if __name__=='__main__':main()
