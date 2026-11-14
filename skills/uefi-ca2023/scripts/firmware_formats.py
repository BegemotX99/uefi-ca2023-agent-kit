"""AMI FFS and signature-list parsing adapted from the PLATON X99 project."""
from hashlib import sha256
from pathlib import Path
from uuid import UUID
import struct
import lzma

MIB = 1024 * 1024

FFS2 = UUID("8c8ce578-8a3d-4f1c-9935-896185c32dd3").bytes_le

FFS3 = UUID("5473c07a-3dcb-4dca-bd6f-1e9689e7349a").bytes_le

LZMA = UUID("ee4e5898-3914-4259-9d6e-dc7bd79403cf").bytes_le

AUTH_GUID = UUID("4aafd29d-68df-49ee-8aa9-347d375665a7").bytes_le

X509 = UUID("a5c059a1-94e4-4aa7-87b5-ab155c2bf072").bytes_le

DEFAULT_GUIDS = {
    UUID("cc0f8a3f-3dea-4376-9679-5426ba0a907e").bytes_le: "PK",
    UUID("9fe7de69-0aea-470a-b50a-139813649189").bytes_le: "KEK",
    UUID("fbf95065-427f-47b3-8077-d13c60710998").bytes_le: "db",
    UUID("9d7a05e9-f740-44c3-858b-75586a8f9c8e").bytes_le: "dbx",
}

CERTIFICATES = {
    "KEK": {
        "Microsoft KEK 2K CA 2023": "3cd3f0309edae228767a976dd40d9f4affc4fbd5218f2e8cc3c9dd97e8ac6f9d",
    },
    "db": {
        "Windows UEFI CA 2023": "076f1fea90ac29155ebf77c17682f75f1fdd1be196da302dc8461e350a9ae330",
        "Microsoft UEFI CA 2023": "f6124e34125bee3fe6d79a574eaa7b91c0e7bd9d929c1a321178efd611dad901",
        "Microsoft Option ROM UEFI CA 2023": "e5be3e64c6e66a281457ecdece0d6d0787577aad2a3a0144262c10c14ba8d8f1",
    },
}

DEFAULT_LIMIT = MIB

FACTORY_KEYS = {
    "PK": "26383b3012f68c75a44e07fe02572167388a43fc77bb112c218ae0bb5fb2a42d",
    "KEK": "8599624905e4fa11b379471f80f870369cc046d1ed45fefe540072a6784934bf",
    "db": "5dbc0253a9bb2a84e03522cfc37a3b5be3b1088ecfcd753d08f1425cdef2b5c1",
    "dbx": "9d1ae9179583bea1df91a12c4ab83937f21569024eea92e3476cd1707790703a",
}

AMI_KEY_VOLUME = UUID("5c60f367-a505-419a-859e-2a4ff6ca6fe5").bytes_le

DRIVER_GUIDS = tuple(UUID(value).bytes_le for value in (
    "1807040d-5934-41a2-a088-8e0f777f71ab",  # NVRAMDxe
    "447a1b58-8f3e-4658-abaa-9e7b2280b90a",  # NVRAMSmm
    "4551f2f5-c684-4f27-936f-c7b04a5c5ff1",  # SecureBootDXE
))

def digest(data):
    return sha256(data).hexdigest()

def read_image(path):
    with path.open("rb") as stream:
        data = stream.read(64 * MIB + 1)
    if not data or len(data) > 64 * MIB:
        raise ValueError("Expected a nonempty firmware image of at most 64 MiB.")
    return data

def intel_bios_region(data):
    if data[0x10:0x14] != b"\x5a\xa5\xf0\x0f" or len(data) < 0x1000:
        return None
    region_table = ((struct.unpack_from("<I", data, 0x14)[0] >> 16) & 0xff) * 16
    if not 0x20 <= region_table <= 0xff8:
        return None
    reg = struct.unpack_from("<I", data, region_table + 4)[0]
    start = (reg & 0x7fff) * 0x1000
    end = (((reg >> 16) & 0x7fff) + 1) * 0x1000
    return (start, end) if 0x1000 <= start < end <= len(data) else None

def bios_start(data):
    region = intel_bios_region(data)
    if len(data) == 16 * MIB and region == (8 * MIB, 16 * MIB):
        return 8 * MIB
    elif len(data) == 8 * MIB and data[0x10:0x14] != b"\x5a\xa5\xf0\x0f":
        return 0
    return None

def volumes(data, start, end):
    cursor = start
    while (sig := data.find(b"_FVH", cursor, end)) >= 0:
        cursor = sig + 4
        base = sig - 40
        if base < start or base + 56 > end:
            continue
        fs = data[base+16:base+32]
        length = struct.unpack_from("<Q", data, base + 32)[0]
        attrs, header_size, _, ext = struct.unpack_from("<IHHH", data, base + 44)
        if (fs not in (FFS2, FFS3) or data[base+55] != 2 or header_size < 56
                or header_size % 2 or not header_size <= length <= end - base):
            continue
        if sum(struct.unpack_from(f"<{header_size//2}H", data, base)) & 0xffff:
            continue
        first = header_size
        if ext:
            if not 56 <= ext <= length - 20:
                continue
            ext_size = struct.unpack_from("<I", data, base + ext + 16)[0]
            if not 20 <= ext_size <= length - ext:
                continue
            first = max(first, ext + ext_size)
        yield base, base + length, base + ((first + 7) & ~7), fs, 0xff if attrs & 0x800 else 0
        cursor = base + length

def ffs_files(data, volume):
    base, end, offset, fs, erased = volume
    while offset + 24 <= end:
        header = data[offset:offset+24]
        if header == bytes([erased]) * 24:
            break
        size = int.from_bytes(header[20:23], "little")
        attrs = header[19]
        header_len = 24
        extra = b""
        if attrs & 1:
            if fs != FFS3 or offset + 32 > end:
                raise ValueError("Unsupported extended FFS header")
            extra = data[offset+24:offset+32]
            size = int.from_bytes(extra, "little")
            header_len = 32
        if size < header_len or offset + size > end:
            raise ValueError("Invalid FFS file length")
        if sum(header[:17] + header[18:23] + extra) & 0xff:
            raise ValueError("Invalid FFS header checksum")
        body = data[offset+header_len:offset+size]
        next_offset = base + ((offset - base + size + 7) & ~7)
        if next_offset > end:
            raise ValueError("FFS padding extends past the volume")
        valid = ((sum(body) + header[17]) & 0xff) == 0 if attrs & 0x40 else header[17] == 0xaa
        yield offset, next_offset, header, body, valid
        offset = next_offset
    if data[offset:end] != bytes([erased]) * (end - offset):
        raise ValueError("Firmware volume tail is not erased")

def raw_payload(data):
    if len(data) < 4:
        raise ValueError("Truncated firmware section")
    size = int.from_bytes(data[:3], "little")
    if not 4 <= size <= len(data):
        raise ValueError("Invalid firmware section length")
    if data[3] == 0x19:
        return data[4:size]
    if data[3] != 2 or size < 24 or data[4:20] != LZMA:
        raise ValueError("Section is outside the supported AMI formats")
    offset = struct.unpack_from("<H", data, 20)[0]
    if not 24 <= offset < size or size - offset > DEFAULT_LIMIT:
        raise ValueError("Invalid compressed section size")
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=64 * MIB)
    plain = decoder.decompress(data[offset:size], max_length=DEFAULT_LIMIT + 1)
    if len(plain) > DEFAULT_LIMIT or not decoder.eof or len(plain) < 4 or plain[3] != 0x19:
        raise ValueError("Unsupported compressed raw section")
    return raw_payload(plain)

def signature_lists(data):
    """Return the EFI signature list payload and fingerprints of its X.509 entries."""
    if len(data) >= 40 and data[24:40] == AUTH_GUID:
        size, revision, kind = struct.unpack_from("<IHH", data, 16)
        if not (24 <= size < len(data) - 16 and revision == 0x200 and kind == 0xef1):
            raise ValueError("Invalid Auth2 header")
        data = data[16+size:]
    if not data or len(data) > DEFAULT_LIMIT:
        raise ValueError("Unsupported EFI signature database size")
    certs = []
    count = 0
    pos = 0
    while pos < len(data):
        if pos + 28 > len(data):
            raise ValueError("Truncated EFI signature list")
        size, header, record = struct.unpack_from("<III", data, pos + 16)
        entries = size - 28 - header
        if record <= 16 or entries < record or entries % record or pos + size > len(data):
            raise ValueError("Invalid EFI signature list")
        count += entries // record
        if data[pos:pos+16] == X509:
            for entry in range(pos+28+header, pos+size, record):
                certs.append(digest(data[entry+16:entry+record]))
        pos += size
    return data, count, certs

def make_ffs(guid, kind, body):
    header = bytearray(guid + bytes((0, 0xaa, kind, 0)) +
                       (24+len(body)).to_bytes(3, "little") + b"\xf8")
    header[16] = -sum(header[:17] + header[18:23]) & 0xff
    return bytes(header) + body
