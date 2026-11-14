"""Part definitions are exact: no guessed aliases or relaxed identity guards."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'usb_creator'))
from flash_parts import add_reviewed_parts,ENTRY

class FlashParts(unittest.TestCase):
    def test_append_preserves_existing_table(self):
        original=b'; vendor table\r\nW25Q128, 0xEF4018, 0x8000000, 0x1000, 0x20, 64, 0\r\n'
        result=add_reviewed_parts(original)
        self.assertTrue(result.startswith(original));self.assertTrue(result.endswith(ENTRY))
        self.assertEqual(result.count(b'0xA12818'),1)
    def test_idempotent(self):
        result=add_reviewed_parts(b'; empty table')
        self.assertEqual(add_reviewed_parts(result),result)
    def test_conflicting_parameters_or_names_refused(self):
        for row in (ENTRY.replace(b'0x8000000',b'0x4000000'),ENTRY.replace(b'0x20',b'0xD8'),ENTRY.replace(b'0xA12818',b'0xA14018'),ENTRY.replace(b'FM25W128',b'OTHER')):
            with self.assertRaisesRegex(ValueError,'Conflicting'):add_reviewed_parts(row)
    def test_duplicate_or_malformed_refused(self):
        for table in (ENTRY+ENTRY,b'INVALID, 0x10\n',b'BAD, XX, 1, 2, 3, 4, 5\n'):
            with self.assertRaises(ValueError):add_reviewed_parts(table)

if __name__=='__main__':unittest.main()
