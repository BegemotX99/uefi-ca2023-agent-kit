"""Saving through the GUI must preserve source identity and never overwrite."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
from portable_engine import save_candidate,kit


class PortableSave(unittest.TestCase):
    def fixture(self,folder):
        source=folder/'stock.bin';source.write_bytes(b'original fixture')
        image=b'verified candidate fixture'
        report=dict(input_sha256=kit.digest(source.read_bytes()),sha256=kit.digest(image),size=len(image))
        return source,image,report

    def test_save_and_readback_with_sidecars(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source,image,report=self.fixture(folder)
            paths=save_candidate(source,folder/'new.bin',image,report,'all checks passed')
            self.assertEqual(paths[0].read_bytes(),image)
            self.assertTrue(all(p.exists() for p in paths))
            self.assertEqual(source.read_bytes(),b'original fixture')

    def test_refuses_input_name_existing_sidecar_or_changed_input(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source,image,report=self.fixture(folder)
            with self.assertRaises(ValueError):save_candidate(source,source,image,report,'log')
            output=folder/'new.bin';Path(str(output)+'.log.txt').write_text('existing')
            with self.assertRaises(ValueError):save_candidate(source,output,image,report,'log')
            self.assertFalse(output.exists())
            source.write_bytes(b'changed input')
            with self.assertRaisesRegex(ValueError,'Input changed'):save_candidate(source,folder/'other.bin',image,report,'log')

    def test_refuses_modified_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source,image,report=self.fixture(folder)
            with self.assertRaisesRegex(ValueError,'Candidate identity'):
                save_candidate(source,folder/'new.bin',image+b'bad',report,'log')

    def test_partial_save_is_rolled_back(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source,image,report=self.fixture(folder)
            output=folder/'new.bin';real_open=Path.open
            def open_file(path,*args,**kwargs):
                if path.name.endswith('.report.json') and args and args[0]=='xb':raise OSError('simulated report write failure')
                return real_open(path,*args,**kwargs)
            with patch.object(Path,'open',open_file):
                with self.assertRaises(OSError):save_candidate(source,output,image,report,'log')
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(),b'original fixture')


if __name__=='__main__':unittest.main()
