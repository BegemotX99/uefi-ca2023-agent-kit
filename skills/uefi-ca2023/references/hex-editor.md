# Manual hex-editor workflow

A hex editor writes prepared bytes into a firmware image. First generate complete, validated factory key files using the layout and signing workflow in this skill. Changing a DER blob by hand requires rebuilding its containing ESL, authentication signature, sections, compression and FFS headers.

1. Record full input size and hash, and work on a copy. Open the source in UEFITool to identify its real physical allocations.
2. Prepare and verify the new binary file objects. For growth, prove the GUID lookup and select erased, unallocated space inside the active firmware volume.
3. Prepare valid pad files for retired factory file slots. The same GUID must resolve uniquely to the intended replacement.
4. In HxD, use Select Block with hexadecimal start and length, then Paste Write at the intended destination offset. Use overwrite operations and keep total image size fixed. Copy all headers, pads and alignment bytes in the approved range. [HxD](https://mh-nexus.de/en/hxd/)
5. Re-extract every modified object, validate checksums and signatures, compare full image ranges, and record the final SHA-256. When reproducing a reference candidate, require its exact hash.

## Historical H9S002 example

For the **November** `qiyida-x99-h9s-20251103-003048.rom`, input SHA-256 is `f5a9b5ca654fe5c9b280a8b7d09139ec092773f64cf855c4c1596c086f1cb1c3`. Copying these ranges from that project's verified donor image reproduced output `69a3d3ce636440680c9c6c76190f59973ddd709bc60268bd065b32bc2e7a3f82`.

| Range purpose | Start | Last byte inclusive | Length |
|---|---|---|---|
| Retired PK/KEK/db slots with valid pads | B7A150 | B7BC57 | 1B08 |
| New authenticated key files | BCE9F0 | BD142F | 2A40 |

The donor firmware is outside this repository. These values describe a single previously signed artifact. A freshly generated key or signature usually changes file sizes and hashes. Recompute the complete placement for new builds, other revisions and BIOS-region-only files. The stock dbx in this example begins immediately after the first range at B7BC58.
