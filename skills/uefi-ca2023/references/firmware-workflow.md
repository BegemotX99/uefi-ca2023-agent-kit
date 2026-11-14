# Firmware layout, native enrollment and image construction

## Establish the input

Record the motherboard model and revision, image origin, full length, SHA-256, embedded build ID and build date. A download's filename date can describe a dump or upload rather than firmware compilation. Extract containers as binary files. An Intel descriptor can map an 8 MiB BIOS inside a 16 MiB SPI image, but that geometry is specific to each input.

The reviewed examples use a BIOS region at `[0x800000, 0x1000000)` and an AMI FFS2 volume at `[0x890000, 0xD90000)`. Their saved variable banks precede that volume. These offsets are evidence for those images. Derive every offset again for a new board or build.

## Locate the correct factory defaults

Use UEFITool NE and UEFIExtract to walk file and section nesting. The supplied inspector walks directly visible FFS2/FFS3 volumes and reads AMI factory files with raw or supported GUID-defined LZMA sections. It records parsing failures. It has no capsule decryption or general nested-volume extraction. [UEFITool source](https://github.com/LongSoft/UEFITool)

| Variable | Reviewed AMI factory FFS GUID |
|---|---|
| PK | `CC0F8A3F-3DEA-4376-9679-5426BA0A907E` |
| KEK | `9FE7DE69-0AEA-470A-B50A-139813649189` |
| db | `FBF95065-427F-47B3-8077-D13C60710998` |
| dbx | `9D7A05E9-F740-44C3-858B-75586A8F9C8E` |

These are storage-file identities. Variable namespace GUIDs and certificate owner GUIDs have different purposes. PK/KEK use `EFI_GLOBAL_VARIABLE`, while db/dbx use `EFI_IMAGE_SECURITY_DATABASE_GUID`. GUIDs serialize with UEFI's mixed-endian byte layout. A generic UUID text search in compressed firmware may miss the object.

Require exactly one intended key set within the reviewed active volume. Recovery copies, duplicate volumes, raw certificate blobs and saved NVRAM can create ambiguous search hits. Trace the Restore Factory Keys path to the storage objects it actually reads. Other vendors can use different files or include the defaults in executable resources.

## Review the native code

The original workflow examined `SecureBootDXE`, `NVRAMDxe` and `NVRAMSmm`. The three reviewed driver GUIDs are recorded in `scripts/firmware_formats.py`. Validate file and PE hashes. If the hashes differ, decompress the binaries, compare code/data with appropriate relocation handling and locate the relevant enrollment routines. Timestamps, load addresses, compression output and padding can change hashes without changing a routine's behavior.

The H9S002 SecureBootDXE executable differed from H9S001 only in five timestamp bytes. Its NVRAM drivers also contained other differences, so the workflow exercised their actual Setup Mode Auth2 parser routines separately. Isolated emulation supplied the proper ABI, pointer-to-buffer arguments, lengths, attributes and Setup Mode state. Valid KEK/db updates returned their expected EFI signature-list payloads. Corrupted certificate GUIDs and malformed list lengths were rejected.

Those experiments establish a parser result. Enforcing a signer in User Mode, full physical enrollment ordering and POST require separate evidence. Verify the signed content cryptographically as well as exercising the native parser. Keep emulator addresses and function contracts pinned to the executable hash that was reviewed.

## Build the storage objects

1. Decode the factory lists and inventory every original entry. Preserve the requested trust baseline.
2. Resolve the owner policy in [certificates-and-signing.md](certificates-and-signing.md).
3. Build the replacement EFI signature lists and any required Auth2 wrapper. Verify the signed variable name, GUID, attributes, timestamp and payload.
4. Rebuild section sizes and compression. In the reviewed AMI files, the stack is FFS file, GUID-defined LZMA section, raw section and Auth2 object.
5. Recalculate FFS length and header checksum, applicable data checksum, and 8-byte file alignment. Respect 4-byte section alignment inside section streams. A volume checksum only changes when its header changes. [UEFI PI storage format](https://uefi.org/specs/PI/1.8/V3_Design_Discussion.html)
6. If the object outgrows its old allocation, prove that the native reader finds it by GUID. Retire the old file allocation with a valid FFS pad file. Append the replacement inside verified erased space in the same volume. Preserve all surrounding file offsets. A run of FF bytes inside another file is still allocated data.
7. Enumerate the output from scratch. Require exactly one active default for each variable, valid checksums, matching decoded payloads and enough unallocated volume tail.

The supplied builder restricts input to the exact review records and native driver hashes. It always creates its own owner-PK migration with fresh local signatures. Editing the manifest to accept an arbitrary image defeats that review requirement. Use [board-review.md](board-review.md) to establish new evidence first.

## Verify the entire artifact

Compare the full input and output byte arrays. Every changed byte must belong to an approved old factory file allocation or new tail allocation. Check image length, Intel descriptor, ME, saved variables, executable FFS files, factory dbx and FIT entries against the stated scope. Reopen with an independent parser and investigate every new diagnostic.

The FIT checks in the supplied script detect selected boot-policy and key-manifest record types. Absence of those entries alone proves neither universal absence of verified boot nor permission to edit signed vendor capsules. Inspect any additional authenticated structures and platform verification requirements.

Save under a new filename, with an input hash, output hash, offsets, new certificate identities, owner-key fingerprint and validation status. Package the exact full SPI image if that was requested. Physical flashing requires a tool and procedure appropriate for the exact board and flash chip.
