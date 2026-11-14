"""Portable Windows GUI for the current validated auto-detect backend."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from uuid import uuid4

from portable_engine import PortableEngine, save_candidate, kit

VERSION='1.0.0'


def resource_root():
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent/'resources'))


class App:
    def __init__(self,root,engine):
        self.root,self.engine=root,engine
        self.messages=queue.Queue()
        self.candidate=None
        self.owner_key=self.owner_cert=None
        self.busy=False
        self.source=tk.StringVar()
        self.owner=tk.StringVar(value='Your encrypted owner key: create a new pair or load an existing pair.')
        self.consent=tk.BooleanVar(value=False)
        self.status=tk.StringVar(value='Open a stock BIOS image to begin.')
        root.title('UEFI CA 2023 Auto Detect — '+VERSION)
        root.geometry('1040x760'); root.minsize(850,620)
        style=ttk.Style(root)
        if 'vista' in style.theme_names():style.theme_use('vista')
        root.configure(background='#eef2f8')
        header=tk.Frame(root,bg='#12203b',padx=24,pady=18)
        header.pack(fill='x')
        tk.Label(header,text='UEFI CA 2023',font=('Segoe UI',23,'bold'),bg='#12203b',fg='white').pack(anchor='w')
        tk.Label(header,text='AUTO DETECT  /  Open → Analyse → Save a new verified image',font=('Segoe UI',11),bg='#12203b',fg='#b9d4ff').pack(anchor='w',pady=(4,0))
        page=ttk.Frame(root,padding=20);page.pack(fill='both',expand=True)
        page.columnconfigure(0,weight=1);page.rowconfigure(4,weight=1)
        picker=ttk.Frame(page);picker.grid(row=0,column=0,sticky='ew');picker.columnconfigure(0,weight=1)
        ttk.Entry(picker,textvariable=self.source,state='readonly').grid(row=0,column=0,sticky='ew')
        self.open_button=ttk.Button(picker,text='Open...',command=self.choose);self.open_button.grid(row=0,column=1,padx=(10,0))
        keys=ttk.LabelFrame(page,text='Owner key — private keys stay on your PC',padding=10)
        keys.grid(row=1,column=0,sticky='ew',pady=12);keys.columnconfigure(0,weight=1)
        ttk.Label(keys,textvariable=self.owner,wraplength=650).grid(row=0,column=0,sticky='w')
        self.create_button=ttk.Button(keys,text='Create owner keys...',command=self.create_owner)
        self.create_button.grid(row=0,column=1,padx=6)
        self.load_button=ttk.Button(keys,text='Load owner keys...',command=self.load_owner)
        self.load_button.grid(row=0,column=2)
        self.consent_button=ttk.Checkbutton(keys,text='Replace the factory AMI test PK with my selected owner certificate.',variable=self.consent)
        self.consent_button.grid(row=1,column=0,columnspan=3,sticky='w',pady=(10,0))
        actions=ttk.Frame(page);actions.grid(row=2,column=0,sticky='ew',pady=(0,10))
        self.analyse_button=ttk.Button(actions,text='Analyse',command=self.analyse,state='disabled');self.analyse_button.pack(side='left')
        self.save_button=ttk.Button(actions,text='Save As...',command=self.save,state='disabled');self.save_button.pack(side='left',padx=10)
        self.spinner=ttk.Progressbar(actions,mode='indeterminate',length=190);self.spinner.pack(side='right')
        ttk.Label(page,text='Analysis log',font=('Segoe UI',10,'bold')).grid(row=3,column=0,sticky='w',pady=(0,5))
        self.log=scrolledtext.ScrolledText(page,wrap='word',font=('Consolas',10),bg='#101b2f',fg='#dceaff',insertbackground='white',padx=12,pady=12,state='disabled')
        self.log.grid(row=4,column=0,sticky='nsew')
        ttk.Label(page,textvariable=self.status,wraplength=960).grid(row=5,column=0,sticky='ew',pady=(12,0))
        self.write('Portable build '+VERSION+' — Python, OpenSSL and UEFIExtract included.\n'
                   'Only compatible reviewed AMI enrollment families are writable. Unknown layouts stay inspection-only.\n'
                   'No hardware flashing or enrolled-key changes are performed by this application.\n')
        root.after(100,self.poll)

    def write(self,message,clear=False):
        self.log.configure(state='normal')
        if clear:self.log.delete('1.0','end')
        self.log.insert('end',message+'\n');self.log.see('end');self.log.configure(state='disabled')

    def set_busy(self,value):
        self.busy=value
        for button in (self.open_button,self.create_button,self.load_button,self.consent_button):
            button.configure(state='disabled' if value else 'normal')
        self.analyse_button.configure(state='normal' if self.source.get() and not value else 'disabled')
        self.save_button.configure(state='normal' if self.candidate and not value else 'disabled')
        if value:self.spinner.start(12)
        else:self.spinner.stop()

    def worker(self,operation,success):
        self.set_busy(True)
        def run():
            try:self.messages.put((success,operation()))
            except Exception as error:self.messages.put(('error',str(error)))
        threading.Thread(target=run,daemon=True).start()

    def choose(self):
        name=filedialog.askopenfilename(parent=self.root,title='Open stock BIOS image',filetypes=[('BIOS images','*.bin *.rom *.fd *.cap'),('All files','*.*')])
        if name:
            self.source.set(name);self.candidate=None;self.set_busy(False)
            self.write('Input selected: '+name,clear=True);self.status.set('Click Analyse to inspect the image.')

    def create_owner(self):
        folder=filedialog.askdirectory(parent=self.root,title='Choose a private folder for your encrypted owner keys')
        if not folder:return
        name=simpledialog.askstring('Owner name','Public owner certificate name:',initialvalue='My motherboard Secure Boot owner',parent=self.root)
        if not name:return
        first=simpledialog.askstring('Private-key password','Enter a password of at least 12 characters:',show='*',parent=self.root)
        if first is None:return
        second=simpledialog.askstring('Repeat password','Repeat the private-key password:',show='*',parent=self.root)
        if first!=second or len(first.encode())<12:
            messagebox.showerror('Password','Passwords must match and contain at least 12 bytes.',parent=self.root);return
        stem='secure-boot-owner-'+uuid4().hex[:10]
        key,cert=Path(folder)/(stem+'.key.pem'),Path(folder)/(stem+'.der')
        args=argparse.Namespace(key=key,cert=cert,name=name)
        self.status.set('Generating an encrypted local owner key...')
        def generate():
            result=kit.generate_owner(args,password=first.encode())
            return key,cert,result['sha256']
        self.worker(generate,'owner-created')

    def load_owner(self):
        key=filedialog.askopenfilename(parent=self.root,title='Select encrypted owner private PEM',filetypes=[('Encrypted PEM','*.pem'),('All files','*.*')])
        if not key:return
        cert=filedialog.askopenfilename(parent=self.root,title='Select matching public DER certificate',filetypes=[('DER certificate','*.der'),('All files','*.*')])
        if cert:self.set_owner(Path(key),Path(cert))

    def set_owner(self,key,cert):
        self.owner_key,self.owner_cert=key,cert
        self.owner.set('Public owner certificate: '+cert.name)
        self.candidate=None;self.set_busy(False)
        self.write('Owner certificate selected: '+str(cert))
        self.write('PK policy: replace factory AMI test PK with this owner; confirm the checkbox before preparing a patch.')
        self.status.set('Owner keys selected. Click Analyse.')

    def analyse(self):
        self.candidate=None
        self.write('Input: '+self.source.get(),clear=True)
        self.write('1. Inspect SPI/FIT, key files, native enrollment family and factory baseline.')
        self.status.set('Analysing image...')
        source=self.source.get()
        self.worker(lambda:self.engine.inspect(source),'inspection')

    def finish_inspection(self,report):
        self.write(json.dumps(report,indent=2))
        self.set_busy(False)
        eligibility=report['automatic_patch']
        if eligibility['status']!='eligible':
            self.status.set('Inspection only — '+eligibility['reason']);return
        if not self.owner_key or not self.owner_cert:
            self.status.set('Layout eligible. Create or load your owner keys, then click Analyse again.');return
        if not self.consent.get():
            self.status.set('Layout eligible. Confirm the owner-PK replacement checkbox, then click Analyse again.');return
        password=simpledialog.askstring('Unlock owner key','Private PEM key password (used locally for this analysis):',show='*',parent=self.root)
        if password is None:
            self.status.set('Preparation cancelled; no image saved.');return
        self.write('2. Prepare and verify a new signed candidate in memory.')
        self.status.set('Signing and validating candidate...')
        source,key,cert=self.source.get(),self.owner_key,self.owner_cert
        self.worker(lambda:self.engine.prepare(source,key,cert,password.encode(),report['sha256'],lambda line:self.messages.put(('log',line))),'candidate')

    def save(self):
        if not self.candidate:return
        source=Path(self.source.get())
        name=filedialog.asksaveasfilename(parent=self.root,title='Save new verified BIOS image',initialdir=source.parent,initialfile=source.stem+'-ca2023.bin',defaultextension='.bin',confirmoverwrite=False,filetypes=[('BIOS image','*.bin')])
        if not name:return
        image,report=self.candidate
        log=self.log.get('1.0','end-1c')
        self.status.set('Saving verified image, report and log...')
        self.worker(lambda:save_candidate(source,name,image,report,log),'saved')

    def poll(self):
        try:
            while True:
                kind,result=self.messages.get_nowait()
                if kind=='log':self.write(result)
                elif kind=='inspection':self.finish_inspection(result)
                elif kind=='owner-created':
                    key,cert,fingerprint=result;self.set_owner(key,cert)
                    self.write('Encrypted private key saved locally. Public certificate SHA-256: '+fingerprint)
                elif kind=='candidate':
                    self.candidate=result;self.set_busy(False)
                    self.write('Result: verified offline candidate, '+str(len(result[0]))+' bytes.')
                    self.write('Factory defaults are patched; physical board/enrollment/Windows testing remains separate.')
                    self.status.set('All validation checks passed. Save As is ready.')
                elif kind=='saved':
                    self.set_busy(False)
                    for path in result:self.write('Saved and read back: '+str(path))
                    self.status.set('Saved image, JSON report and analysis log. Original preserved.')
                elif kind=='error':
                    self.candidate=None;self.set_busy(False);self.write('STOPPED: '+result)
                    self.status.set('Stopped — no verified image is ready to save.')
        except queue.Empty:pass
        self.root.after(100,self.poll)


def self_test(engine,output,image=None,test_dir=None):
    """Exercise the shipped runtime; optional firmware stays outside the bundle."""
    result=dict(version=VERSION,checks=[])
    def passed(name):result['checks'].append(name)
    try:
        root=tk.Tk();root.withdraw()
        app=App(root,engine);root.update()
        assert str(app.analyse_button['state'])=='disabled' and str(app.save_button['state'])=='disabled'
        root.destroy();passed('Tk GUI creates Open/Analyse/Save/log and starts with Save disabled')
        subprocess.run([kit.OPENSSL,'version'],check=True,capture_output=True,creationflags=kit.PROCESS_FLAGS)
        passed('Bundled native OpenSSL runs without PATH lookup')
        subprocess.run([str(engine.extractor),'--version'],check=True,capture_output=True,creationflags=kit.PROCESS_FLAGS)
        passed('Bundled UEFIExtract runs without PATH lookup')
        pinned={sha for values in kit.CERTIFICATES.values() for sha in values.values()}
        assert {kit.digest(p.read_bytes()) for p in engine.certificates.glob('*.der')}==pinned
        passed('All four bundled Microsoft DER certificates match pinned fingerprints')
        with tempfile.TemporaryDirectory(prefix='ca2023-self-test-') as temp:
            folder=Path(temp);key,cert=folder/'owner.pem',folder/'owner.der'
            password=b'Ephemeral-package-test-2026'
            kit.generate_owner(argparse.Namespace(key=key,cert=cert,name='Ephemeral package self-test'),password=password)
            passed('Fresh encrypted local RSA owner key generation')
            from cryptography import x509
            from cryptography.hazmat.primitives import serialization
            private=serialization.load_pem_private_key(key.read_bytes(),password=password)
            certificate=x509.load_der_x509_certificate(cert.read_bytes())
            payload=kit.esl(cert.read_bytes())
            assert kit.signature_lists(kit.auth2('KEK',payload,private,certificate))[0]==payload
            passed('Auth2 signing and independent bundled OpenSSL verification')
            if image:
                report=engine.inspect(image)
                result['input_sha256']=report['sha256'];result['eligibility']=report['automatic_patch']
                if report['automatic_patch']['status']=='eligible':
                    candidate,details=engine.prepare(image,key,cert,password,report['sha256'],lambda line:None)
                    passed('Complete candidate build with all backend and independent parser checks')
                    if test_dir:
                        dest=Path(test_dir);dest.mkdir(parents=True,exist_ok=True)
                        paths=save_candidate(image,dest/(Path(image).stem+'-SELFTEST.bin'),candidate,details,'Ephemeral-key package self-test. Offline only; do not flash.\n')
                        passed('Save image/report/log and verify readback; input preserved')
                        result['test_outputs']=[str(p) for p in paths]
                else:
                    passed('Unsupported image remains inspection-only; no output saved')
        result['status']='PASS'
    except Exception as error:
        result.update(status='FAIL',error=str(error))
    Path(output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return 0 if result['status']=='PASS' else 1


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--self-test',type=Path,help='Write packaged-runtime validation JSON')
    parser.add_argument('--image',type=Path,help='Optional local image for self-test; never included in release')
    parser.add_argument('--test-dir',type=Path,help='Optional self-test output folder; candidates use discarded test keys')
    parser.add_argument('--resources',type=Path,help='Resource root for source-development runs')
    args=parser.parse_args()
    try:engine=PortableEngine(args.resources or resource_root())
    except Exception as error:
        if args.self_test:
            args.self_test.write_text(json.dumps(dict(status='FAIL',error=str(error))))
        else:
            root=tk.Tk();root.withdraw();messagebox.showerror('Package incomplete',str(error));root.destroy()
        return 1
    if args.self_test:return self_test(engine,args.self_test,args.image,args.test_dir)
    root=tk.Tk();App(root,engine);root.mainloop();return 0


if __name__=='__main__':
    raise SystemExit(main())
