"""Prism Windows USB creator. No device write occurs without explicit confirmation."""
import argparse
import ctypes
from datetime import datetime
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from PIL import Image,ImageTk

from core import load_assets,selected_files,build_image,MIB
from windows_disk import enumerate_usb,blocked_reason,identity,prepare_physical_usb

BG='#0d1727';PANEL='#15253a';LINE='#2a415b';FG='#e9f0f8';MUTED='#a3b7cc';ACCENT='#068f98'


def resource_root():return Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'usb-assets'


class App:
    def __init__(self,root,assets):
        self.root,self.assets=root,Path(assets);self.manifest=load_assets(assets)
        self.board_id='f8';self.drives=[];self.messages=queue.Queue();self.busy=False;self.photos={};self.cards={}
        self.drive_var=tk.StringVar();self.erase=tk.BooleanVar(value=False);self.status=tk.StringVar(value='Choose a motherboard and refresh the USB drive list.')
        root.title('Prism SPI Flash USB Creator 1.0.0')
        root.geometry(str(min(1120,root.winfo_screenwidth()-60))+'x'+str(min(850,root.winfo_screenheight()-100)))
        root.minsize(900,600);root.configure(bg=BG)
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('Prism.TCombobox',fieldbackground=PANEL,background=PANEL,foreground=FG,arrowcolor=FG,padding=9)
        style.map('Prism.TCombobox',fieldbackground=[('readonly',PANEL)],foreground=[('readonly',FG)])
        style.configure('Prism.Horizontal.TProgressbar',background=ACCENT,troughcolor=PANEL,bordercolor=PANEL,lightcolor=ACCENT,darkcolor=ACCENT)
        top=tk.Frame(root,bg=BG,padx=25,pady=18);top.pack(fill='x')
        tk.Label(top,text='PRISM / SPI',font=('Segoe UI',22,'bold'),bg=BG,fg=FG).pack(side='left')
        tk.Label(top,text='USB CREATOR   •   FULL 16 MiB',font=('Segoe UI',10),bg=BG,fg=MUTED).pack(side='left',padx=20)
        self.admin_button=tk.Button(top,text='Run as administrator',command=self.elevate,bg=PANEL,fg=FG,relief='flat',padx=12,pady=8)
        self.admin_button.pack(side='right')
        if self.is_admin():self.admin_button.configure(text='Administrator',state='disabled')
        body=tk.Frame(root,bg=BG);body.pack(fill='both',expand=True)
        canvas=tk.Canvas(body,bg=BG,highlightthickness=0)
        scrollbar=ttk.Scrollbar(body,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        content=tk.Frame(canvas,bg=BG,padx=25,pady=15)
        content_window=canvas.create_window((0,0),window=content,anchor='nw')
        canvas.bind('<Configure>',lambda event:canvas.itemconfigure(content_window,width=event.width))
        content.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
        content.columnconfigure(0,weight=7);content.columnconfigure(1,weight=4);content.rowconfigure(0,weight=1)
        left=tk.Frame(content,bg=BG);left.grid(row=0,column=0,sticky='nsew',padx=(0,22))
        right=tk.Frame(content,bg=PANEL,highlightbackground=LINE,highlightthickness=1);right.grid(row=0,column=1,sticky='nsew')
        tk.Label(left,text='One USB. Full BIOS control.',font=('Segoe UI',20,'bold'),bg=BG,fg=FG).pack(anchor='w')
        tk.Label(left,text='Built-in tested firmware • FreeDOS backup and write menu',font=('Segoe UI',10),bg=BG,fg=MUTED).pack(anchor='w',pady=(4,18))
        tk.Label(left,text='01  CHOOSE YOUR MOTHERBOARD',font=('Segoe UI',10,'bold'),bg=BG,fg=MUTED).pack(anchor='w',pady=(0,8))
        grid=tk.Frame(left,bg=BG);grid.pack(fill='x');grid.columnconfigure(0,weight=1);grid.columnconfigure(1,weight=1)
        for index,board in enumerate(self.manifest['boards']):
            image=Image.open(self.assets/board['photo']).convert('RGBA');image.thumbnail((91,103))
            photo=ImageTk.PhotoImage(image);self.photos[board['id']]=photo
            card=tk.Frame(grid,bg=PANEL,highlightthickness=2,highlightbackground=LINE,padx=8,pady=10)
            card.grid(row=index//2,column=index%2,sticky='nsew',padx=(0 if index%2==0 else 5,5 if index%2==0 else 0),pady=5)
            pic=tk.Label(card,image=photo,bg=PANEL);pic.pack(side='left',padx=(0,9))
            text=tk.Frame(card,bg=PANEL);text.pack(side='left',fill='both',expand=True)
            title=tk.Label(text,text=board['short'],font=('Segoe UI',12,'bold'),bg=PANEL,fg=FG,anchor='w',wraplength=145,justify='left');title.pack(anchor='w')
            info=tk.Label(text,text='CA 2023\n16 MiB full SPI',font=('Segoe UI',10),bg=PANEL,fg=MUTED,justify='left');info.pack(anchor='w',pady=(5,0))
            for widget in (card,pic,text,title,info):widget.bind('<Button-1>',lambda e,ident=board['id']:self.choose_board(ident))
            self.cards[board['id']]=card
        tk.Label(left,text='02  USB DRIVE — ALL CONTENTS WILL BE ERASED',font=('Segoe UI',10,'bold'),bg=BG,fg=MUTED).pack(anchor='w',pady=(18,7))
        drive_row=tk.Frame(left,bg=BG);drive_row.pack(fill='x')
        self.drive_picker=ttk.Combobox(drive_row,textvariable=self.drive_var,state='readonly',style='Prism.TCombobox');self.drive_picker.pack(side='left',fill='x',expand=True)
        self.drive_picker.bind('<<ComboboxSelected>>',lambda e:self.drive_changed())
        self.refresh_button=tk.Button(drive_row,text='↻ Refresh',command=self.refresh,bg=PANEL,fg=FG,relief='flat',padx=15,pady=10);self.refresh_button.pack(side='left',padx=(8,0))
        self.drive_info=tk.Label(left,text='Internal disks are excluded. USB identity is rechecked before any write.',font=('Segoe UI',9),bg=BG,fg=MUTED,wraplength=640,justify='left');self.drive_info.pack(anchor='w',pady=(8,12))
        tk.Label(left,text='PREPARATION LOG',font=('Segoe UI',10,'bold'),bg=BG,fg=MUTED).pack(anchor='w',pady=(0,6))
        self.log=tk.Text(left,height=7,bg='#091323',fg='#c9e5ef',font=('Consolas',9),relief='flat',padx=12,pady=10,wrap='word',state='disabled');self.log.pack(fill='both',expand=True)
        self.confirm=tk.Checkbutton(left,text='I understand the selected USB will be formatted.',variable=self.erase,command=self.update_ready,bg=BG,fg=FG,selectcolor=PANEL,activebackground=BG,activeforeground=FG,font=('Segoe UI',10));self.confirm.pack(anchor='w',pady=(14,10))
        self.create_button=tk.Button(left,text='Create bootable USB',command=self.prepare,bg=ACCENT,fg='white',disabledforeground='#7c9aaf',font=('Segoe UI',12,'bold'),relief='flat',pady=12,state='disabled');self.create_button.pack(fill='x')
        self.progress=ttk.Progressbar(left,mode='indeterminate',style='Prism.Horizontal.TProgressbar');self.progress.pack(fill='x',pady=(9,0))
        tk.Label(right,text='FREEDOS BOOT MENU',font=('Segoe UI',10,'bold'),bg=PANEL,fg=MUTED).pack(anchor='w',padx=20,pady=(20,12))
        tk.Label(right,text='PRISM / SPI FLASH',font=('Consolas',16,'bold'),bg=PANEL,fg='#4bd7d7').pack(anchor='w',padx=20)
        self.preview=tk.Text(right,bg=PANEL,fg=FG,font=('Consolas',11),wrap='word',relief='flat',padx=20,pady=20,height=21,state='disabled');self.preview.pack(fill='both',expand=True)
        tk.Label(right,text='Prebuilt images use the author’s Secure Boot key. Build with your own key to control Secure Boot yourself.',font=('Segoe UI',9),bg=PANEL,fg=MUTED,wraplength=315,justify='left').pack(anchor='w',padx=20,pady=(8,15))
        tk.Label(right,text='Legacy / CSM boot required\nFreeDOS is not a UEFI application.',font=('Segoe UI',10,'bold'),bg=PANEL,fg='#dbbb7b',justify='left').pack(anchor='w',padx=20,pady=(0,20))
        tk.Label(root,textvariable=self.status,font=('Segoe UI',10),bg=BG,fg=MUTED,anchor='w',wraplength=1060).pack(fill='x',padx=25,pady=(0,15))
        self.choose_board('f8');self.write('Embedded assets verified. No drive has been modified.\nRefresh lists physical USB devices only.')
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll);self.refresh()

    @staticmethod
    def is_admin():
        try:return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except AttributeError:return False

    def elevate(self):
        exe=sys.executable;params='' if getattr(sys,'frozen',False) else subprocess.list2cmdline([str(Path(__file__).resolve())])
        fn=ctypes.windll.shell32.ShellExecuteW
        fn.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_int];fn.restype=ctypes.c_void_p
        result=fn(None,'runas',exe,params,None,1) or 0
        if result<=32:messagebox.showerror('Administrator access','Elevation was cancelled or could not start.',parent=self.root)
        else:self.root.destroy()

    def write(self,text):
        self.log.configure(state='normal');self.log.insert('end',text+'\n');self.log.see('end');self.log.configure(state='disabled')

    def choose_board(self,ident):
        if self.busy:return
        self.board_id=ident
        for key,card in self.cards.items():card.configure(highlightbackground=ACCENT if key==ident else LINE)
        board=next(b for b in self.manifest['boards'] if b['id']==ident)
        text='PREPARED FOR\n'+board['name']+'\n\nBIOS.BIN\n16,777,216 bytes\n\n1  BACKUP ENTIRE 16 MiB\n   Save a new BACKnnnn.BIN\n\n2  WRITE ENTIRE 16 MiB\n   Type FLASH to confirm\n   Full-chip readback verification\n\n0  EXIT TO DOS\n\nFACTORY.BIN is included as an\noriginal reference, not a backup\nof your physical board.\n'
        self.preview.configure(state='normal');self.preview.delete('1.0','end');self.preview.insert('end',text);self.preview.configure(state='disabled')

    def selected_drive(self):
        try:
            index=self.drive_picker.current()
            return self.drives[index] if index>=0 else None
        except (IndexError,TypeError):return None

    def drive_changed(self):self.erase.set(False);self.update_ready()

    def update_ready(self):
        disk=self.selected_drive();reason=blocked_reason(disk) if disk else 'Select a USB drive'
        if disk:self.drive_info.configure(text='Disk '+str(disk['number'])+' · '+disk['model']+' · serial '+disk['serial']+((' · BLOCKED: '+reason) if reason else ''))
        ready=not self.busy and disk is not None and not reason and self.erase.get() and self.is_admin()
        self.create_button.configure(state='normal' if ready else 'disabled')
        if disk and not reason and not self.is_admin():self.status.set('Run as administrator before USB preparation. Listing drives is read-only.')

    def worker(self,operation,result):
        self.busy=True;self.refresh_button.configure(state='disabled');self.drive_picker.configure(state='disabled');self.confirm.configure(state='disabled');self.update_ready();self.progress.start(15)
        def work():
            try:self.messages.put((result,operation()))
            except Exception as error:self.messages.put(('error',str(error)))
        threading.Thread(target=work,daemon=True).start()

    def refresh(self):
        if self.busy:return
        self.erase.set(False);self.status.set('Refreshing physical USB devices...')
        self.worker(enumerate_usb,'drives')

    def prepare(self):
        disk=self.selected_drive()
        if self.busy or disk is None or not self.erase.get():return
        reason=blocked_reason(disk)
        if reason:messagebox.showerror('Drive blocked',reason,parent=self.root);return
        phrase='ERASE '+str(disk['number'])
        answer=simpledialog.askstring('Confirm USB format',
            'All partitions and files on this USB will be erased.\n\n'+disk['model']+'\nDisk '+str(disk['number'])+' · '+str(round(disk['size']/1024**3,2))+' GiB\nSerial: '+disk['serial']+'\n\nType '+phrase+' to prepare it.',parent=self.root)
        if answer!=phrase:self.status.set('Cancelled. No drive was changed.');return
        expected=dict(disk);board_id=self.board_id
        self.status.set('Preparing selected USB. Do not disconnect it.')
        def prepare():
            emit=lambda message:self.messages.put(('log',message))
            load_assets(self.assets)
            board,files=selected_files(self.assets,self.manifest,board_id)
            emit('Selected motherboard: '+board['name'])
            with tempfile.TemporaryDirectory(prefix='prism-usb-') as temp:
                image=Path(temp)/'prepared.img'
                result=build_image(image,expected['size'],files,(self.assets/'mbr-code.bin').read_bytes(),(self.assets/'fd-boot32.bin').read_bytes(),emit)
                prepare_physical_usb(expected,image,result['used_end'],emit)
            return board['name']
        self.worker(prepare,'prepared')

    def poll(self):
        try:
            while True:
                kind,result=self.messages.get_nowait()
                if kind=='log':self.write(result);continue
                self.busy=False;self.progress.stop();self.refresh_button.configure(state='normal');self.drive_picker.configure(state='readonly');self.confirm.configure(state='normal')
                if kind=='drives':
                    self.drives=result
                    labels=[]
                    for d in result:
                        letters=','.join(x+':' for x in d['letters']) or 'No letter';why=blocked_reason(d)
                        labels.append(letters+' · '+d['model']+' · '+str(round(d['size']/1024**3,1))+' GiB · Disk '+str(d['number'])+(' [blocked]' if why else ''))
                    self.drive_picker.configure(values=labels);self.drive_var.set('');self.status.set(str(len(result))+' USB device(s) found. Select the intended drive.')
                elif kind=='prepared':
                    self.erase.set(False);self.write('SUCCESS: boot files, image and filesystem readback verified.')
                    self.status.set('USB ready for '+result+'. Safely remove it, then use the non-UEFI Legacy/CSM boot entry.')
                elif kind=='error':self.erase.set(False);self.write('STOPPED: '+result);self.status.set('Stopped: '+result)
                self.update_ready()
        except queue.Empty:pass
        self.root.after(100,self.poll)

    def close(self):
        if self.busy:messagebox.showinfo('Operation in progress','Wait until the operation finishes before closing.',parent=self.root)
        else:self.root.destroy()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--assets',type=Path);parser.add_argument('--self-test',type=Path);parser.add_argument('--image-dir',type=Path)
    args=parser.parse_args();assets=args.assets or resource_root()
    if args.self_test:
        report={'status':'FAIL','checks':[]}
        try:
            m=load_assets(assets);report['checks'].append('All embedded binaries, photos and four BIOS pairs verified')
            root=tk.Tk();root.withdraw();app=App(root,assets);root.update()
            assert len(app.cards)==4 and str(app.create_button['state'])=='disabled'
            root.destroy();report['checks'].append('Prism GUI, four motherboard photos and protected initial state')
            if args.image_dir:
                args.image_dir.mkdir(parents=True,exist_ok=True)
                for b in m['boards']:
                    _,files=selected_files(assets,m,b['id']);out=args.image_dir/(b['id']+'.img')
                    meta=build_image(out,256*MIB,files,(assets/'mbr-code.bin').read_bytes(),(assets/'fd-boot32.bin').read_bytes())
                    assert meta['files']['BIOS.BIN']['sha256']==b['sha256'];report['checks'].append('Boot image and file readback: '+b['id'])
            report['status']='PASS'
        except Exception as error:report['error']=str(error)
        args.self_test.write_text(json.dumps(report,indent=2)+'\n');return 0 if report['status']=='PASS' else 1
    root=tk.Tk()
    try:App(root,assets)
    except Exception as error:root.withdraw();messagebox.showerror('Prism could not start',str(error));root.destroy();return 1
    root.mainloop();return 0


if __name__=='__main__':raise SystemExit(main())
