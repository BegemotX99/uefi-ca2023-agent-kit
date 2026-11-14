"""QEMU-only integration tests; local images and file-backed FPT fixture only."""
import argparse,hashlib,json,os,struct,subprocess,time
from pathlib import Path
from core import build_image,load_assets,selected_files,MIB

def read_file(image,name):
    with image.open('rb') as f:
        f.seek(454);start=struct.unpack('<I',f.read(4))[0]*512
        f.seek(start);b=f.read(512);spc=b[13];reserved=struct.unpack_from('<H',b,14)[0]
        fat=start+reserved*512;data=fat+b[16]*struct.unpack_from('<I',b,36)[0]*512
        def chain(c,length=None):
            out=bytearray();seen=set()
            while 2<=c<0xffffff8:
                if c in seen:raise AssertionError('FAT cycle')
                seen.add(c);f.seek(data+(c-2)*spc*512);out.extend(f.read(spc*512))
                if length is not None and len(out)>=length:break
                f.seek(fat+c*4);c=struct.unpack('<I',f.read(4))[0]&0xfffffff
            return bytes(out[:length]) if length is not None else bytes(out)
        root=chain(struct.unpack_from('<I',b,44)[0])
        for offset in range(0,len(root),32):
            entry=root[offset:offset+32]
            if entry[0] in (0,0xe5) or entry[11]&0x18:continue
            filename=entry[:8].decode('ascii').rstrip()+('.'+entry[8:11].decode('ascii').rstrip() if entry[8:11].strip() else '')
            if filename==name:
                c=(struct.unpack_from('<H',entry,20)[0]<<16)|struct.unpack_from('<H',entry,26)[0]
                return chain(c,struct.unpack_from('<I',entry,28)[0])
    return b''

def main():
    p=argparse.ArgumentParser()
    for arg in ('work','assets','qemu','qemu-share','watcom'):p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--cases',nargs='+',choices=['success','corrupt','failure','vendor','parts-mismatch'],default=['success','corrupt','failure','vendor'])
    a=p.parse_args();a.work.mkdir(exist_ok=True,parents=True);source=Path(__file__).parent/'dos'
    env=dict(os.environ,WATCOM=str(a.watcom),INCLUDE=str(a.watcom/'h'),PATH=str(a.watcom/'binnt64')+';'+str(a.watcom/'binnt')+';'+os.environ['PATH'])
    def compile(name,out):subprocess.run([str(a.watcom/'binnt64/wcl.exe'),'-q','-bt=dos','-ms','-3','-otexan','-k16384','-i='+str(a.work),'-fe='+str(out),str(source/name)],cwd=a.work,env=env,check=True)
    stub=a.work/'FPT.EXE';compile('fpt_test_stub.c',stub)
    m=load_assets(a.assets);board,files=selected_files(a.assets,m,'f8');boardhash=hashlib.sha256(files['BIOS.BIN']).hexdigest()
    header='typedef struct {const char *id,*name,*sha256;} Board;\nstatic const Board BOARDS[]={{"f8","FILE-BASED VM TEST","'+boardhash+'"}};\n#define BOARD_COUNT 1\n#define PRISM_SIMULATION 1\n#define FPT_HASH "'+hashlib.sha256(stub.read_bytes()).hexdigest()+'"\n#define PARTS_HASH "'+hashlib.sha256(files['FPARTS.TXT']).hexdigest()+'"\n'
    (a.work/'board_data.h').write_text(header);compile('prism.c',a.work/'PRISM.EXE')
    testfiles=dict(files);testfiles.update({'FPT.EXE':stub.read_bytes(),'PRISM.EXE':(a.work/'PRISM.EXE').read_bytes(),'CHIP.BIN':b'X'*(16*MIB),'VECTOR.TXT':b'abc'})
    testfiles['AUTOEXEC.BAT']=b'@ECHO OFF\r\nCD \\\r\nSET PATH=.;\\\r\nPRISM.EXE --hash VECTOR.TXT > HASH.TXT\r\nPRISM.EXE\r\n'
    results=[]
    for case in a.cases:
        payload=dict(testfiles);payload['MODE.TXT']={'success':b'OK','corrupt':b'CORRUPT','failure':b'FAIL','vendor':b'OK','parts-mismatch':b'OK'}[case]
        if case in ('vendor','parts-mismatch'):payload['FPT.EXE']=files['FPT.EXE'];payload['PRISM.EXE']=files['PRISM.EXE']
        if case=='parts-mismatch':payload['FPARTS.TXT']+=b'; deliberately changed by test\r\n'
        image=a.work/(case+'.img');build_image(image,256*MIB,payload,(a.assets/'mbr-code.bin').read_bytes(),(a.assets/'fd-boot32.bin').read_bytes())
        log=(a.work/(case+'-qemu.log')).open('w')
        proc=subprocess.Popen([str(a.qemu),'-L',str(a.qemu_share),'-m','128','-display','none','-monitor','stdio','-nic','none','-drive','if=ide,file='+str(image)+',format=raw'],stdin=subprocess.PIPE,stdout=log,stderr=log,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def command(text):proc.stdin.write(text+'\n');proc.stdin.flush()
        def key(text):command('sendkey '+text)
        def wait_for(text,timeout=600):
            end=time.monotonic()+timeout
            while time.monotonic()<end:
                if proc.poll() is not None:raise AssertionError('QEMU exited early')
                if text in read_file(image,'FLASH.LOG').decode('ascii',errors='replace'):return
                time.sleep(.5)
            raise AssertionError(case+' timeout: '+text+'\n'+read_file(image,'FLASH.LOG').decode('ascii',errors='replace'))
        try:
            wait_for('PRISM menu started')
            command('screendump '+str(a.work/(case+'-menu.ppm')));time.sleep(.5)
            assert read_file(image,'HASH.TXT').decode().startswith(hashlib.sha256(b'abc').hexdigest())
            if case=='success':
                key('1');wait_for('BACKUP SAVED');key('ret');time.sleep(.6)
                key('1');wait_for('BACK0002.BIN, full');key('ret');time.sleep(.6)
                assert read_file(image,'BACK0001.BIN')==b'X'*(16*MIB)
                assert read_file(image,'BACK0002.BIN')==b'X'*(16*MIB)
                key('2');wait_for('Waiting for typed FLASH');key('ret');wait_for('Write cancelled');key('ret');time.sleep(.6)
                assert read_file(image,'CHIP.BIN')==b'X'*(16*MIB)
            key('2' if case in ('success','corrupt') else '1')
            if case in ('success','corrupt'):
                end=time.monotonic()+600;needed=2 if case=='success' else 1
                while read_file(image,'FLASH.LOG').count(b'Waiting for typed FLASH')<needed:
                    if time.monotonic()>end:raise AssertionError('Confirmation timeout')
                    time.sleep(.5)
                for char in 'FLASH':key('shift-'+char.lower());time.sleep(.15)
                key('ret');wait_for('SUCCESS:' if case=='success' else 'READBACK VERIFICATION FAILED',600)
                if case=='success':assert read_file(image,'CHIP.BIN')==files['BIOS.BIN']
            elif case=='parts-mismatch':
                wait_for('STOPPED: FPARTS.TXT was changed')
                assert b'FPT.EXE -d' not in read_file(image,'FLASH.LOG')
            else:
                wait_for('BACKUP FAILED');assert b'FPT return status: 0;' not in read_file(image,'FLASH.LOG')
            command('screendump '+str(a.work/(case+'.ppm')));time.sleep(.5)
            results.append(dict(case=case,status='PASS',log=read_file(image,'FLASH.LOG').decode('ascii',errors='replace')))
            print(case,'PASS',flush=True)
        finally:
            if proc.poll() is None:
                command('screendump '+str(a.work/(case+'-last.ppm')));time.sleep(.5)
                command('quit');proc.wait(timeout=15)
            log.close()
        (a.work/'REPORT.json').write_text(json.dumps(results,indent=2)+'\n')
    print('All VM scenarios passed. No physical USB or SPI device was opened.')
if __name__=='__main__':main()
