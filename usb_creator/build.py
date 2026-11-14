"""Build the self-contained Windows EXE from verified public release inputs.

Example: python usb_creator/build.py --assets INPUTS/assets --watcom C:/WATCOM
No drive inventory or raw device access is performed by this build script.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from core import load_assets

def main():
    p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,required=True);p.add_argument('--watcom',type=Path,required=True)
    p.add_argument('--work',type=Path,default=Path('artifacts/prism-build'));p.add_argument('--output',type=Path,default=Path('artifacts/prism-dist'))
    a=p.parse_args();a.work=a.work.resolve();a.output=a.output.resolve();a.watcom=a.watcom.resolve()
    source=Path(__file__).resolve().parent;manifest=load_assets(a.assets)
    a.work.mkdir(parents=True,exist_ok=True);a.output.mkdir(parents=True,exist_ok=True)
    assets=a.work/'usb-assets'
    if assets.exists():raise FileExistsError('Choose a new work directory; existing assets are not overwritten')
    shutil.copytree(a.assets,assets)
    header='typedef struct {const char *id,*name,*sha256;} Board;\nstatic const Board BOARDS[]={\n'
    header+=',\n'.join('{'+','.join(json.dumps(b[k]) for k in ('id','name','sha256'))+'}' for b in manifest['boards'])+'\n};\n#define BOARD_COUNT 4\n#define PRISM_SIMULATION 0\n'
    for macro,name in [('FPT_HASH','FPT.EXE'),('PARTS_HASH','FPARTS.TXT')]:header+='#define '+macro+' "'+hashlib.sha256((assets/name).read_bytes()).hexdigest()+'"\n'
    (a.work/'board_data.h').write_text(header)
    env=dict(os.environ,WATCOM=str(a.watcom),INCLUDE=str(a.watcom/'h'),PATH=str(a.watcom/'binnt64')+';'+str(a.watcom/'binnt')+';'+os.environ['PATH'])
    subprocess.run([str(a.watcom/'binnt64/wcl.exe'),'-q','-bt=dos','-ms','-3','-otexan','-k16384','-i='+str(a.work),'-fe='+str(assets/'PRISM.EXE'),str(source/'dos/prism.c')],cwd=a.work,env=env,check=True)
    # Replace only our source members, retaining the exact FreeDOS source archives.
    with zipfile.ZipFile(assets/'SOURCE.ZIP') as z:members={n:z.read(n) for n in z.namelist() if not n.startswith('prism/')}
    for name in ('prism.c','sha256.h'):members['prism/'+name]=(source/'dos'/name).read_bytes()
    members['prism/board_data.h']=header.encode();members['prism/LICENSE.txt']=(source.parent/'LICENSE').read_bytes()
    with zipfile.ZipFile(assets/'SOURCE.ZIP','w',zipfile.ZIP_DEFLATED) as z:
        for name,data in members.items():z.writestr(name,data)
    manifest['files']=[dict(path=f.relative_to(assets).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in sorted(assets.rglob('*')) if f.is_file() and f.name!='manifest.json']
    (assets/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');load_assets(assets)
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--exclude-module','numpy','--name','Prism-USB-Creator','--paths',str(source),'--add-data',str(assets)+';usb-assets','--distpath',str(a.output),'--workpath',str(a.work/'pyinstaller'),'--specpath',str(a.work),str(source/'gui.py')],check=True)
    exe=a.output/'Prism-USB-Creator.exe';report={'exe':exe.name,'size':exe.stat().st_size,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'boards':manifest['boards'],'boot':'Legacy/CSM FreeDOS; not native UEFI','physical_usb_test':'pending','physical_spi_test_of_this_menu':'pending'}
    (a.output/'BUILD-REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('exe','size','sha256')},indent=2))
if __name__=='__main__':main()
