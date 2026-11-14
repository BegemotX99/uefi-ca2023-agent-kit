"""Inspect AMI factory defaults and build reviewed CA 2023 migration candidates."""
import argparse
from datetime import datetime, timezone, timedelta
import getpass
import json
import lzma
from pathlib import Path
import struct
import subprocess
import tempfile
from uuid import UUID

from firmware_formats import (
    AMI_KEY_VOLUME, AUTH_GUID, CERTIFICATES, DEFAULT_GUIDS, DRIVER_GUIDS, FACTORY_KEYS,
    FFS2, LZMA, X509, digest, ffs_files, intel_bios_region, make_ffs, read_image,
    raw_payload, signature_lists, volumes,
)

REFERENCES = Path(__file__).resolve().parent.parent / 'references'
GLOBAL = UUID('8be4df61-93ca-11d2-aa0d-00e098032b8c').bytes_le
SECURITY = UUID('d719b2cb-3d3a-4596-a3bc-dad00e67656f').bytes_le
OWNER = UUID('77fa9abd-0359-4d32-bd60-28f4e78f784b').bytes_le


def reviewed(data):
    region = intel_bios_region(data)
    start = region[0] if region else 0
    return next((item for item in json.loads((REFERENCES/'reviewed-images.json').read_text())
                 if digest(data) == item['sha256'] or
                 (len(data) == 0x800000 and digest(data[start:]) == item['bios_sha256'])), None)


def inventory(data):
    start, end = intel_bios_region(data) or (0, len(data))
    found = []
    errors = []
    for volume in volumes(data, start, end):
        try:
            for offset, _, header, body, valid in ffs_files(data, volume):
                name = DEFAULT_GUIDS.get(header[:16])
                if name:
                    if not valid or header[18] != 2 or header[23] != 0xf8:
                        raise ValueError(f'Invalid factory FFS file at {offset:#x}')
                    payload, count, certificates = signature_lists(raw_payload(body))
                    found.append(dict(variable=name, offset=offset, volume=volume[0],
                                      entries=count, sha256=digest(payload),
                                      certificates={title: fingerprint in certificates
                                                    for title, fingerprint in CERTIFICATES.get(name, {}).items()}))
        except (ValueError, lzma.LZMAError) as error:
            errors.append(dict(volume=volume[0], error=str(error)))
    return dict(size=len(data), sha256=digest(data), bios_region=intel_bios_region(data),
                reviewed_image=reviewed(data), factory_defaults=found, parse_errors=errors,
                interpretation='Factory defaults only. Enrolled NVRAM and Windows servicing need separate verification.')


def prepare_layout(data):
    profile = reviewed(data)
    if profile is None:
        raise ValueError('Input is outside the supplied image review records. Complete a new board review first.')
    start, end = intel_bios_region(data) or (0, len(data))
    fit = struct.unpack_from('<Q', data, len(data)-0x40)[0]-(2**32-len(data))
    if not start <= fit < end-0x40 or data[fit:fit+8] != b'_FIT_   ':
        raise ValueError('Invalid FIT pointer')
    count = int.from_bytes(data[fit+8:fit+11], 'little')
    if not 1 <= count <= 256 or fit+16*count > end-0x40:
        raise ValueError('Invalid FIT size')
    if any(data[fit+14+16*i]&127 in (0x0b, 0x0c, 0x10) for i in range(count)):
        raise ValueError('Signed boot-policy/key-manifest FIT entry requires its own review')
    report = inventory(data)
    found = report['factory_defaults']
    if report['parse_errors'] or sorted(item['variable'] for item in found) != sorted(FACTORY_KEYS):
        raise ValueError('Expected exactly one complete readable factory key set')
    volume = next(v for v in volumes(data,start,end) if v[0]==found[0]['volume'])
    if any(item['volume'] != volume[0] for item in found):
        raise ValueError('Factory keys span multiple volumes')
    ext = struct.unpack_from('<H',data,volume[0]+52)[0]
    if (volume[3] != FFS2 or volume[4] != 0xff or not ext or volume[1] > fit
            or data[volume[0]+ext:volume[0]+ext+16] != AMI_KEY_VOLUME):
        raise ValueError('Unexpected AMI volume layout')
    files = list(ffs_files(data,volume))
    if not all(item[-1] for item in files):
        raise ValueError('Invalid FFS checksum')
    drivers = {str(UUID(bytes_le=h[:16])):digest(h+b) for _,_,h,b,_ in files if h[:16] in DRIVER_GUIDS}
    if drivers != profile['driver_hashes']:
        raise ValueError('Enrollment driver fingerprints differ')
    slots = {DEFAULT_GUIDS[h[:16]]:(offset,nxt,h,raw_payload(body))
             for offset,nxt,h,body,_ in files if h[:16] in DEFAULT_GUIDS}
    if any(signature_lists(slots[name][3])[0] == b'' or
           digest(signature_lists(slots[name][3])[0]) != expected for name,expected in FACTORY_KEYS.items()):
        raise ValueError('Factory certificate baseline differs')
    return profile, volume, files, slots


def esl(certificate):
    return X509+struct.pack('<III',44+len(certificate),0,16+len(certificate))+OWNER+certificate


def write_new(path, data):
    with path.open('xb') as stream:
        stream.write(data)
    if path.read_bytes() != data:
        raise ValueError(f'File readback failed for {path}')


def generate_owner(args):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    if args.key.exists() or args.cert.exists() or args.key.resolve() == args.cert.resolve():
        raise ValueError('Choose two distinct unused owner-key paths')
    password = getpass.getpass('Password for the encrypted private PEM key: ').encode()
    if len(password) < 12 or password != getpass.getpass('Repeat password: ').encode():
        raise ValueError('Use a matching password of at least 12 bytes')
    key = rsa.generate_private_key(public_exponent=65537,key_size=3072)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME,args.name)])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
            .sign(key,hashes.SHA256()))
    private = key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                                serialization.BestAvailableEncryption(password))
    public = cert.public_bytes(serialization.Encoding.DER)
    write_new(args.key, private)
    write_new(args.cert, public)
    print(json.dumps(dict(public_certificate=str(args.cert),sha256=digest(public)),indent=2))


def auth2(name, payload, key, cert):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.serialization import pkcs7
    now = datetime.now(timezone.utc)
    timestamp = struct.pack('<HBBBBBBIhBB',now.year,now.month,now.day,now.hour,now.minute,now.second,0,0,0,0,0)
    content = name.encode('utf-16le')+(GLOBAL if name in ('PK','KEK') else SECURITY)+struct.pack('<I',0x27)+timestamp+payload
    cms = (pkcs7.PKCS7SignatureBuilder().set_data(content).add_signer(cert,key,hashes.SHA256())
           .sign(serialization.Encoding.DER,[pkcs7.PKCS7Options.DetachedSignature,
                                           pkcs7.PKCS7Options.Binary,pkcs7.PKCS7Options.NoCapabilities]))
    # Legacy AMI expects bare SignedData inside the WIN_CERTIFICATE_UEFI_GUID.
    def der_body(data, offset):
        length = data[offset+1]
        header = 2
        if length&128:
            n = length&127
            length = int.from_bytes(data[offset+2:offset+2+n],'big')
            header += n
        return data[offset+header:offset+header+length]
    outer = der_body(cms,0)
    if not outer.startswith(bytes.fromhex('06092a864886f70d010702a0')):
        raise ValueError('Unexpected PKCS#7 ContentInfo encoding')
    signed_data = der_body(outer,11)
    if not signed_data.startswith(b'\x30'):
        raise ValueError('Unexpected SignedData structure')
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder/'message.bin').write_bytes(content)
        (folder/'signature.der').write_bytes(cms)
        subprocess.run(['openssl','cms','-verify','-binary','-inform','DER','-in',str(folder/'signature.der'),
                        '-content',str(folder/'message.bin'),'-noverify','-out',str(folder/'verified.bin')],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        if (folder/'verified.bin').read_bytes() != content:
            raise ValueError('Signed-content verification failed')
    return timestamp+struct.pack('<IHH',24+len(signed_data),0x200,0xef1)+AUTH_GUID+signed_data+payload


def pack_default(header, auth):
    raw = (4+len(auth)).to_bytes(3,'little')+b'\x19'+auth
    compressed = lzma.compress(raw,format=lzma.FORMAT_ALONE)
    compressed = compressed[:5]+len(raw).to_bytes(8,'little')+compressed[13:]
    body = (24+len(compressed)).to_bytes(3,'little')+b'\x02'+LZMA+struct.pack('<HH',24,1)+compressed
    if raw_payload(body) != auth:
        raise ValueError('Compression readback failed')
    return make_ffs(header[:16],2,body)


def build(args):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    if not args.replace_platform_key:
        raise ValueError('This builder implements owner-PK migration. Explicit --replace-platform-key is required.')
    if args.output.exists() or args.report.exists() or args.output.resolve()==args.report.resolve():
        raise ValueError('Output image and report need distinct unused paths')
    data = read_image(args.image)
    profile, volume, files, slots = prepare_layout(data)
    cert = x509.load_der_x509_certificate(args.owner_cert.read_bytes())
    password = getpass.getpass('Private PEM key password: ').encode()
    key = serialization.load_pem_private_key(args.owner_key.read_bytes(),password=password)
    if not isinstance(key,rsa.RSAPrivateKey) or key.key_size<2048 or key.public_key().public_numbers()!=cert.public_key().public_numbers():
        raise ValueError('Expected matching RSA owner key and certificate, at least 2048 bits')
    now = datetime.now(timezone.utc)
    if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
        raise ValueError('Owner certificate is outside its validity interval')
    expected = {title:sha for variable in CERTIFICATES.values() for title,sha in variable.items()}
    certificates = {}
    for path in args.certificates.glob('*.der'):
        payload = path.read_bytes()
        fingerprint = digest(payload)
        if fingerprint in expected.values():
            x509.load_der_x509_certificate(payload)
            certificates[fingerprint] = payload
    if set(certificates)!=set(expected.values()):
        raise ValueError('Directory must contain the four pinned Microsoft 2023 DER certificates')
    old = {name:signature_lists(item[3])[0] for name,item in slots.items()}
    payloads = dict(old)
    payloads['PK'] = esl(cert.public_bytes(serialization.Encoding.DER))
    for variable, new in CERTIFICATES.items():
        payloads[variable] += b''.join(esl(certificates[fingerprint]) for fingerprint in new.values())
    image = bytearray(data)
    tail = files[-1][1]
    original_tail = tail
    replacements = {}
    for name in ('PK','KEK','db'):
        offset, nxt, header, _ = slots[name]
        packed = pack_default(header,auth2(name,payloads[name],key,cert))
        aligned = packed+b'\xff'*(-len(packed)%8)
        if tail+len(aligned)>volume[1]:
            raise ValueError('Insufficient erased space for new factory files')
        image[offset:nxt] = make_ffs(bytes(16),0xf0,b'\xff'*(nxt-offset-24))
        image[tail:tail+len(aligned)] = aligned
        replacements[name] = tail
        tail += len(aligned)
    image = bytes(image)
    final = list(ffs_files(image,volume))
    if not all(ok for *_,ok in final) or len(final)!=len(files)+3:
        raise ValueError('Final FFS inventory failed')
    for off,nxt,header,_,_ in files:
        if header[:16] not in [g for g,n in DEFAULT_GUIDS.items() if n in replacements] and image[off:nxt]!=data[off:nxt]:
            raise ValueError('Unrelated firmware file changed')
    replay = bytearray(data)
    for name in replacements:
        off,nxt,_,_=slots[name]
        replay[off:nxt]=image[off:nxt]
    replay[original_tail:tail]=image[original_tail:tail]
    if image!=replay or len(image)!=len(data) or list(volumes(image,*(intel_bios_region(data) or (0,len(data)))))!=list(volumes(data,*(intel_bios_region(data) or (0,len(data))))):
        raise ValueError('Unexpected image layout or changed ranges')
    report = inventory(image)
    for name,payload in payloads.items():
        matches=[f for f in report['factory_defaults'] if f['variable']==name]
        if len(matches)!=1 or matches[0]['sha256']!=digest(payload):
            raise ValueError(f'{name} payload readback failed')
    if report['parse_errors']:
        raise ValueError('Output parse errors')
    changed_ranges = []
    begin = None
    for offset, (before, after) in enumerate(zip(data, image)):
        if before != after and begin is None:
            begin = offset
        elif before == after and begin is not None:
            changed_ranges.append([begin, offset])
            begin = None
    if begin is not None:
        changed_ranges.append([begin, len(image)])
    report.update(base_profile=profile['id'],input_sha256=digest(data),
                  pk_replaced=True,owner_certificate_sha256=digest(args.owner_cert.read_bytes()),
                  validation='Offline candidate. This invocation has no physical board test result.',
                  replacement_offsets=replacements,changed_ranges=changed_ranges,
                  range_convention='Half-open byte offsets [start, end)',
                  modified_allocations={name:list(slots[name][:2]) for name in replacements},
                  appended_allocation=[original_tail,tail])
    # Build and verify everything in memory before creating either deliverable.
    write_new(args.output,image)
    write_new(args.report,(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(dict(output=str(args.output),sha256=digest(image),size=len(image),report=str(args.report)),indent=2))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    modes=cli.add_subparsers(dest='mode',required=True)
    inspect=modes.add_parser('inspect')
    inspect.add_argument('image',type=Path)
    keygen=modes.add_parser('keygen')
    keygen.add_argument('--name',required=True)
    keygen.add_argument('--key',type=Path,required=True)
    keygen.add_argument('--cert',type=Path,required=True)
    patch=modes.add_parser('build')
    patch.add_argument('image',type=Path)
    patch.add_argument('output',type=Path)
    patch.add_argument('--report',type=Path,required=True)
    patch.add_argument('--owner-key',type=Path,required=True)
    patch.add_argument('--owner-cert',type=Path,required=True)
    patch.add_argument('--certificates',type=Path,required=True)
    patch.add_argument('--replace-platform-key',action='store_true')
    args=cli.parse_args()
    try:
        if args.mode=='inspect':
            print(json.dumps(inventory(read_image(args.image)),indent=2))
        elif args.mode=='keygen':
            generate_owner(args)
        else:
            build(args)
    except (ValueError,OSError,lzma.LZMAError,subprocess.CalledProcessError) as error:
        cli.exit(1,f'Error: {error}\n')


if __name__=='__main__':
    main()
