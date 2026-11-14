"""Layout-family recognition without trusting whole-image hashes."""
from pathlib import Path
import subprocess
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/uefi-ca2023/scripts'))
import firmware_formats as f
import uefi_ca2023 as kit


def fixture(base=0x1000, duplicate=None, change_driver=False, change_keys=False, dirty_tail=False):
    image = bytearray(b'\xff'*0x10000)
    end = base+0x5000
    header = bytearray(0x48)
    header[16:32] = f.FFS2
    struct.pack_into('<Q4sIHHH',header,32,end-base,b'_FVH',0x800,0x48,0,0x48)
    header[55] = 2
    struct.pack_into('<II',header,56,1,end-base)
    struct.pack_into('<H',header,50,-sum(struct.unpack('<36H',header))&0xffff)
    image[base:base+len(header)] = header
    image[base+0x48:base+0x5c] = f.AMI_KEY_VOLUME+struct.pack('<I',20)
    cursor = base+0x60
    baseline, drivers, offsets = {}, {}, {}
    chunks = []
    for guid, name in f.DEFAULT_GUIDS.items():
        payload = kit.esl(('fixture '+name).encode())
        baseline[name] = f.digest(payload)
        if change_keys and name == 'KEK':
            payload = kit.esl(b'changed trust policy')
        file = kit.pack_default(f.make_ffs(guid,2,b'')[:24],payload)
        chunks.append((name,file))
        if duplicate == name:
            chunks.append((name+' duplicate',file))
    for index,guid in enumerate(f.DRIVER_GUIDS):
        file = f.make_ffs(guid,7,b'enrollment fixture '+bytes([index]))
        drivers[str(kit.UUID(bytes_le=guid))] = f.digest(file)
        if change_driver and index == 0:
            file = f.make_ffs(guid,7,b'changed enrollment implementation')
        chunks.append(('driver '+str(index),file))
    for name,file in chunks:
        offsets[name] = cursor
        image[cursor:cursor+len(file)] = file
        cursor += (len(file)+7)&~7
    if dirty_tail:
        image[end-1] = 0
    fit = 0xff00
    image[fit:fit+16] = b'_FIT_   '+bytes([1,0,0,0,0,0,0,0])
    struct.pack_into('<Q',image,len(image)-0x40,2**32-len(image)+fit)
    family = dict(id='synthetic-reviewed-family',driver_hashes=drivers)
    return image, baseline, family, offsets


class Detection(unittest.TestCase):
    def prepare(self, image, baseline, family):
        with patch.object(kit,'FACTORY_KEYS',baseline), patch.object(kit,'load_families',return_value=[family]):
            return kit.prepare_layout(bytes(image))

    def test_unlisted_hash_and_different_volume_offsets(self):
        for base in (0x1000,0x2000):
            image, baseline, family, _ = fixture(base)
            image[0x80:0x84] = b'NEW!'
            self.assertIsNone(kit.reviewed(image))
            evidence, volume, _, _ = self.prepare(image,baseline,family)
            self.assertEqual(evidence['enrollment_family'],family['id'])
            self.assertEqual(volume[0],base)
            self.assertIsNone(evidence['historical_image'])

    def test_unknown_native_driver_is_rejected(self):
        image, baseline, family, _ = fixture(change_driver=True)
        with self.assertRaisesRegex(ValueError,'Native enrollment code'):
            self.prepare(image,baseline,family)

    def test_factory_baseline_still_required(self):
        image, baseline, family, _ = fixture(change_keys=True)
        with self.assertRaisesRegex(ValueError,'baseline differs'):
            self.prepare(image,baseline,family)

    def test_duplicate_factory_defaults_are_rejected(self):
        image, baseline, family, _ = fixture(duplicate='db')
        with self.assertRaisesRegex(ValueError,'exactly one'):
            self.prepare(image,baseline,family)

    def test_invalid_ffs_checksum_is_rejected(self):
        image, baseline, family, offsets = fixture()
        image[offsets['driver 0']+16] ^= 1
        with self.assertRaisesRegex(ValueError,'readable factory key set'):
            self.prepare(image,baseline,family)

    def test_non_erased_tail_is_rejected(self):
        image, baseline, family, _ = fixture(dirty_tail=True)
        with self.assertRaisesRegex(ValueError,'readable factory key set'):
            self.prepare(image,baseline,family)

    def test_boot_guard_fit_entry_is_rejected(self):
        image, baseline, family, _ = fixture()
        image[0xff00+14] = 0x0b
        with self.assertRaisesRegex(ValueError,'Signed boot-policy'):
            self.prepare(image,baseline,family)

    def test_duplicate_native_drivers_are_rejected(self):
        _, _, family, _ = fixture()
        files = []
        for guid in f.DRIVER_GUIDS:
            file = f.make_ffs(guid,7,b'driver')
            files.append((0,len(file),file[:24],file[24:],True))
        files.append(files[0])
        with patch.object(kit,'load_families',return_value=[family]):
            with self.assertRaisesRegex(ValueError,'unambiguous'):
                kit.enrollment_family(files)

    def test_family_registry_is_separate_from_image_history(self):
        families = kit.load_families()
        self.assertEqual(len({x['id'] for x in families}),len(families))
        for family in families:
            self.assertEqual(set(family['driver_hashes']),{str(kit.UUID(bytes_le=g)) for g in f.DRIVER_GUIDS})
            self.assertNotIn('sha256',family)
            self.assertNotIn('bios_sha256',family)

    def test_independent_parser_must_produce_reports(self):
        # A process returning success is insufficient evidence of firmware parsing.
        response = subprocess.CompletedProcess([],0,stdout=b'fake version',stderr=b'')
        with patch.object(kit.subprocess,'run',return_value=response):
            with self.assertRaisesRegex(ValueError,'nonempty report'):
                kit.independent_parser(b'input',b'output','unused-parser')

    def test_changed_independent_parser_diagnostics_are_rejected(self):
        calls=[]
        def parser(args,**kwargs):
            if args[-1] == '--version':
                return subprocess.CompletedProcess(args,0,stdout=b'fixture version',stderr=b'')
            path=Path(args[1])
            Path(str(path)+'.report.txt').write_text('fixture tree')
            calls.append(path.name)
            return subprocess.CompletedProcess(args,0,stdout=b'',stderr=b'new error' if len(calls)==2 else b'')
        with patch.object(kit.subprocess,'run',side_effect=parser):
            with self.assertRaisesRegex(ValueError,'diagnostics changed'):
                kit.independent_parser(b'input',b'output','unused-parser')


if __name__=='__main__':
    unittest.main()
