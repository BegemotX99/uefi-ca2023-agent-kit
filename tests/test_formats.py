"""Regression checks for public parsing, signing and refusal behavior."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'skills/uefi-ca2023/scripts'
sys.path.insert(0,str(SCRIPTS))
import firmware_formats as f
import uefi_ca2023 as kit


class Formats(unittest.TestCase):
    def test_signature_list_and_corrupt_length(self):
        payload=kit.esl(b'certificate fixture')
        self.assertEqual(f.signature_lists(payload)[1:],(1,[f.digest(b'certificate fixture')]))
        damaged=bytearray(payload)
        struct.pack_into('<I',damaged,16,len(payload)+1)
        with self.assertRaises(ValueError):
            f.signature_lists(bytes(damaged))

    def test_compressed_default_and_ffs_checksum(self):
        guid=next(iter(f.DEFAULT_GUIDS))
        header=f.make_ffs(guid,2,b'')[:24]
        auth=kit.esl(b'certificate fixture')
        packed=kit.pack_default(header,auth)
        self.assertEqual(f.raw_payload(packed[24:]),auth)
        self.assertEqual(sum(packed[:17]+packed[18:23])&255,0)
        self.assertEqual(int.from_bytes(packed[20:23],'little'),len(packed))

    def test_unknown_input_is_inspection_only(self):
        image=bytes(4096)
        report=kit.inventory(image)
        self.assertIsNone(report['reviewed_image'])
        self.assertEqual(report['factory_defaults'],[])
        with self.assertRaises(ValueError):
            kit.prepare_layout(image)

    def test_existing_output_is_protected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'result'
            path.write_bytes(b'original')
            with self.assertRaises(FileExistsError):
                kit.write_new(path,b'replacement')
            self.assertEqual(path.read_bytes(),b'original')

    def test_manifest_and_public_certificates(self):
        records=json.loads((SCRIPTS.parent/'references/reviewed-images.json').read_text())
        self.assertEqual(len({i['sha256'] for i in records}),len(records))
        for record in records:
            self.assertEqual(len(record['driver_hashes']),3)
        directory=SCRIPTS.parents[2]/'public-owner-certificates'
        for record in json.loads((directory/'manifest.json').read_text()):
            self.assertEqual(f.digest((directory/record['file']).read_bytes()),record['sha256'])

    @unittest.skipUnless(shutil.which('openssl'),'OpenSSL is required for signature validation')
    def test_auth2_verified_signing_roundtrip(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        subject=x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME,'Ephemeral test owner')])
        now=datetime.now(timezone.utc)
        cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
              .serial_number(1).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=1))
              .sign(key,hashes.SHA256()))
        payload=kit.esl(b'certificate fixture')
        wrapped=kit.auth2('KEK',payload,key,cert)
        self.assertEqual(f.signature_lists(wrapped)[0],payload)
        self.assertEqual(wrapped[24:40],f.AUTH_GUID)
        self.assertEqual(struct.unpack_from('<HH',wrapped,20),(0x200,0xef1))


if __name__=='__main__':
    unittest.main()
