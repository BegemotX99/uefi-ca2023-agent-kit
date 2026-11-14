"""Exercise GUI selection/confirmation and preparation against an ordinary file.

The USB inventory and raw-device entry point are mocked. Never formats a drive.
"""
import argparse
import json
from pathlib import Path
import time
import tkinter as tk
from unittest.mock import patch
import gui
from core import make_sparse,MIB
from windows_disk import write_image

def main():
    p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);root=tk.Tk();root.withdraw();calls=[]
    def fake_writer(expected,image,used_end,progress):
        assert expected['serial']=='FILE-ONLY-TEST'
        with (a.output/'simulated-usb.img').open('x+b') as target:
            make_sparse(target);target.truncate(expected['size']);write_image(target,image,used_end,expected['size'],progress)
        calls.append(dict(expected=expected,used_end=used_end))
    try:
        with patch('gui.enumerate_usb',return_value=[]),patch('gui.prepare_physical_usb',side_effect=fake_writer),patch.object(gui.App,'is_admin',return_value=True):
            app=gui.App(root,a.assets)
            def settle():
                end=time.monotonic()+60
                while app.busy and time.monotonic()<end:root.update();time.sleep(.05)
                assert not app.busy,app.status.get()
            settle();assert app.selected_drive() is None
            disk=dict(number=99,serial='FILE-ONLY-TEST',unique_id='test',model='LOCAL TEST FILE',size=256*MIB,sector=512,bus='USB',letters=[],volumes=[])
            app.drives=[disk];app.drive_picker.configure(values=['Local file fixture'])
            # An unset combobox must not implicitly select the final drive.
            assert app.selected_drive() is None
            app.drive_picker.current(0);app.drive_changed();assert not app.erase.get()
            app.choose_board('mr9s');app.erase.set(True);app.update_ready();assert str(app.create_button['state'])=='normal'
            with patch('gui.simpledialog.askstring',return_value='WRONG'):
                app.prepare();assert calls==[] and not app.busy
            with patch('gui.simpledialog.askstring',return_value='ERASE 99'):
                app.prepare();settle()
            assert len(calls)==1 and app.status.get().startswith('USB ready for MACHINIST'),app.status.get()
            assert not app.erase.get()
            report=dict(status='PASS',checks=['No implicit drive selection','Drive-change resets erase approval','Wrong confirmation cancels','Chosen MR9S image prepared via GUI worker','File-only raw writer and readback','Successful completion resets approval'],physical_devices_opened=0)
            (a.output/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:root.destroy()
if __name__=='__main__':main()
