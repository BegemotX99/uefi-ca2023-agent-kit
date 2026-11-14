"""Reviewed FPT part-table additions. Never invent aliases or force a chip ID.

Fudan FM25W128: official flashrom source has FUDAN_ID_NOPREFIX=0xA1,
FUDAN_FM25W128=0x2818, SIZE_16MiB, 256-byte pages, 4 KiB erase 0x20,
and FEATURE_WRSR_WREN (no separate EWSR 0x50 command).
FPT's 64-byte write granularity fits within the device's 256-byte page.
Sources:
https://github.com/flashrom/flashrom/blob/main/include/flashchips.h
https://github.com/flashrom/flashrom/blob/main/flashchips/fudan.c
Manufacturer datasheet: https://www.fmsh.com/nvm/FM25W128_ds_eng.pdf
The manufacturer download was inaccessible during this change; the checked
primary implementation above is the evidence, not a claim of hardware testing.
"""
PART_NAME='FM25W128'
PART_ID=0xA12818
PART_VALUES=(PART_ID,0x8000000,0x1000,0x20,64,0)
ENTRY=b'FM25W128,   0xA12818, 0x8000000, 0x1000, 0x20, 64, 0\r\n'

def add_reviewed_parts(original):
    """Append one reviewed row, preserving every original byte; reject ambiguity."""
    matches=[]
    for line in original.decode('ascii').splitlines():
        line=line.split(';',1)[0].strip()
        if not line:continue
        fields=[x.strip() for x in line.split(',')]
        if len(fields)!=7:raise ValueError('Unexpected FPT table row: '+line)
        try:values=tuple(int(v,0) for v in fields[1:])
        except ValueError:raise ValueError('Invalid FPT numeric field: '+line) from None
        if values[0]==PART_ID or fields[0].casefold()==PART_NAME.casefold():
            if values!=PART_VALUES or fields[0].casefold()!=PART_NAME.casefold():
                raise ValueError('Conflicting FM25W128 name, ID or programming parameters')
            matches.append(line)
    if len(matches)>1:raise ValueError('Duplicate FM25W128 part ID')
    if matches:return original
    return original+(b'' if original.endswith(b'\n') else b'\r\n')+b'; Prism reviewed addition: Fudan FM25W128, JEDEC A1 28 18, 16 MiB\r\n'+ENTRY
