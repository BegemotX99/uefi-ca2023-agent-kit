"""Portable resource binding and save semantics; shared GUI/packaged tests."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

if not getattr(sys,'frozen',False):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/uefi-ca2023/scripts'))
import uefi_ca2023 as kit


class PortableEngine:
    def __init__(self, resources):
        self.resources=Path(resources)
        manifest=json.loads((self.resources/'DEPENDENCIES.json').read_text(encoding='utf-8'))
        for entry in manifest['files']:
            path=(self.resources/entry['path']).resolve()
            if not path.is_relative_to(self.resources.resolve()) or kit.digest(path.read_bytes())!=entry['sha256']:
                raise ValueError('Missing or altered bundled dependency: '+entry['path'])
        self.manifest=manifest
        kit.REFERENCES=self.resources/'references'
        kit.OPENSSL=str(self.resources/'tools/OpenSSL/openssl.exe')
        self.extractor=self.resources/'tools/UEFIExtract.exe'
        self.certificates=self.resources/'microsoft-certificates'

    def inspect(self, source):
        return kit.inventory(kit.read_image(Path(source)))

    def prepare(self, source, owner_key, owner_cert, password, expected_sha256, progress):
        with tempfile.TemporaryDirectory(prefix='ca2023-prepare-') as temp:
            args=argparse.Namespace(image=Path(source), output=Path(temp)/'unused.bin',
                report=Path(temp)/'unused.json',owner_key=Path(owner_key),owner_cert=Path(owner_cert),
                certificates=self.certificates,uefiextract=self.extractor,replace_platform_key=True,
                expected_sha256=expected_sha256)
            return kit.build(args,password=password,save=False,progress=progress)


def save_candidate(source, output, image, report, log):
    """Save only a verified candidate, never overwrite, roll back partial saves."""
    source,output=Path(source),Path(output)
    if source.resolve()==output.resolve():
        raise ValueError('Choose a different filename; the input must remain unchanged')
    if kit.digest(kit.read_image(source))!=report['input_sha256']:
        raise ValueError('Input changed after analysis; analyse it again')
    if kit.digest(image)!=report['sha256'] or len(image)!=report['size']:
        raise ValueError('Candidate identity changed after validation')
    paths=[output,Path(str(output)+'.report.json'),Path(str(output)+'.log.txt')]
    if any(path.exists() for path in paths):
        raise ValueError('Output or sidecar already exists; choose another filename')
    contents=[image,(json.dumps(report,indent=2)+'\n').encode(),log.encode('utf-8')]
    created=[]
    try:
        for path,content in zip(paths,contents):
            with path.open('xb') as stream:
                created.append(path)
                stream.write(content)
            if path.read_bytes()!=content:
                raise ValueError('Saved-file readback failed: '+path.name)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return paths
