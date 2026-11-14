# From Microsoft certificates to a verified firmware candidate

## 1. Obtain the original Microsoft certificates

Use [Microsoft's secureboot_objects repository](https://github.com/microsoft/secureboot_objects), which is linked from [Microsoft's key-management guidance](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-secure-boot-key-creation-and-management-guidance?view=windows-11). These are public X.509 certificates. Microsoft keeps the corresponding private CA keys; you neither obtain nor recreate those keys.

This guide pins upstream commit `3d762aecbaecd12402efd21ba89c8c7bd40da4bd`, inspected on 14 November 2026. Download these four DER files:

| Destination | Original download |
|---|---|
| KEK | [Microsoft Corporation KEK 2K CA 2023](https://raw.githubusercontent.com/microsoft/secureboot_objects/3d762aecbaecd12402efd21ba89c8c7bd40da4bd/PreSignedObjects/KEK/Certificates/microsoft%20corporation%20kek%202k%20ca%202023.der) |
| db | [Windows UEFI CA 2023](https://raw.githubusercontent.com/microsoft/secureboot_objects/3d762aecbaecd12402efd21ba89c8c7bd40da4bd/PreSignedObjects/DB/Certificates/windows%20uefi%20ca%202023.der) |
| db | [Microsoft UEFI CA 2023](https://raw.githubusercontent.com/microsoft/secureboot_objects/3d762aecbaecd12402efd21ba89c8c7bd40da4bd/PreSignedObjects/DB/Certificates/microsoft%20uefi%20ca%202023.der) |
| db | [Microsoft Option ROM UEFI CA 2023](https://raw.githubusercontent.com/microsoft/secureboot_objects/3d762aecbaecd12402efd21ba89c8c7bd40da4bd/PreSignedObjects/DB/Certificates/microsoft%20option%20rom%20uefi%20ca%202023.der) |

Save them together as `.der` files, then compare their SHA-256 values to the complete table in [certificates-and-signing.md](certificates-and-signing.md). Do not substitute an HTML download page, PEM text, an ESL or an Auth2 update for a DER certificate. Microsoft's repository also contains preassembled objects; their wrappers and policies need their own review.

```powershell
Get-FileHash C:\firmware-work\microsoft\*.der -Algorithm SHA256
openssl x509 -inform DER -in C:\firmware-work\microsoft\windows-uefi-2023.der -noout -subject -issuer -dates -fingerprint -sha256
```

The OpenSSL example assumes you saved that certificate under the indicated name. The builder accepts any `.der` filenames and checks certificate bytes.

## 2. Prepare the PC

| Tool | When needed | Role and official source |
|---|---|---|
| Python 3.11+ | All supplied CLI operations | [Python](https://www.python.org/downloads/); inspection uses the standard library. |
| cryptography | Generate owner keys or build images | Install `requirements-build.txt`; [project documentation](https://cryptography.io/en/latest/). |
| OpenSSL | Build and independent signature checks | [OpenSSL](https://www.openssl.org/); make `openssl version` work in the build shell. |
| UEFITool NE and UEFIExtract | Firmware review; UEFIExtract is mandatory for every build | [LongSoft releases](https://github.com/LongSoft/UEFITool/releases); inspect files, decompress sections and compare diagnostics. Supply `--uefiextract PATH` or add it to PATH. NE inspection and legacy editing capabilities differ; this builder constructs files itself. |
| Git | Fetch and pin source revisions | [Git](https://git-scm.com/downloads); optional if using a downloaded source archive. |
| Ghidra and its supported JDK | Unfamiliar enrollment drivers or changed code | [Ghidra releases and install instructions](https://github.com/NationalSecurityAgency/ghidra); decompile extracted PE/TE executables. Use the JDK required by your selected release, rather than assuming a fixed Java version. |
| REA | Optional agent integration for reverse engineering | [REA](https://github.com/morluto/rea); connects an agent to installed analysis engines. A skill alone does not install/register the MCP server or supply Ghidra/Java. Follow that project's client/provider setup. |
| Unicorn, pefile, Capstone | Optional isolated native parser tests | [Unicorn](https://github.com/unicorn-engine/unicorn), [pefile](https://github.com/erocarrera/pefile), [Capstone](https://github.com/capstone-engine/capstone); executable mapping, disassembly and emulation. |
| HxD or another binary editor | Manual review or transplant | Use overwrite mode and the exact image's calculated offsets; see [hex-editor.md](hex-editor.md). |
| Elevated Windows PowerShell | Post-flash verification | Windows SecureBoot cmdlets read enabled state and enrolled variables. |
| Board-compatible flasher/programmer | Physical testing only | Select for the exact board, chip and voltage. It is separate from the image builder and reverse-engineering stack. |

A Ghidra or REA installation is unnecessary to build an image matching a supported enrollment family with this CLI. They become useful when proving support for another implementation. QEMU/OVMF can test generic UEFI applications but cannot reproduce an X99 board's memory training, SPI access policy or vendor enrollment implementation.

```powershell
python --version
python -m pip install -r requirements-build.txt
python -c "import cryptography; print(cryptography.__version__)"
openssl version
python -m unittest discover -s tests -v
```

## 3. Inspect and establish compatibility

```powershell
python skills/uefi-ca2023/scripts/uefi_ca2023.py inspect C:\firmware-work\stock.bin
```

Record board/revision, source, image length, build ID, full hash and SPI map. In UEFITool locate the active factory PK/KEK/db/dbx files and saved NVRAM separately. Extract and decode the factory file sections; search by GUID alone is insufficient. Confirm exactly which objects the factory-key menu reads.

For an unfamiliar image, extract SecureBootDXE, NVRAMDxe and NVRAMSmm and hash their PE/TE bodies as well as FFS containers. In Ghidra or REA trace GUID references through factory file loading, decompression, Auth2 parsing and SetVariable. Establish expected variable attributes, Setup Mode handling, signature encoding and update ordering. Verify whether relocated files are found by GUID. This work produces a board review, rather than permission to bypass a failed fingerprint check. See [firmware-workflow.md](firmware-workflow.md) and [board-review.md](board-review.md).

## 4. Generate owner keys and sign the update objects

Choose PK policy first. This builder replaces the reviewed AMI test PK with a new local owner PK. It does not preserve an OEM PK or authorize an arbitrary live update under an existing owner's policy.

```powershell
python skills/uefi-ca2023/scripts/uefi_ca2023.py keygen --name "My motherboard owner" --key C:\private-keys\owner.key.pem --cert C:\private-keys\owner.der
```

Create the parent directory first. Enter the private-key password when prompted. Publish `owner.der` and its fingerprint if desired; keep `owner.key.pem` and its password private.

The Microsoft certificates already contain Microsoft's signatures. Leave their DER bytes unchanged. The owner signs the **authenticated variable update**, which contains the certificate lists. The signed input is variable name + namespace GUID + attributes + timestamp + ESL payload. The builder generates detached RSA/SHA-256 CMS, verifies it using OpenSSL, then packages the legacy AMI-compatible SignedData into Auth2. A signature on the `.bin` file or the `.der` file alone is a different object and cannot replace this operation. The complete byte structures and the meaning of `-noverify` appear in [the signing reference](certificates-and-signing.md).

## 5. Implement the factory defaults in the firmware

```powershell
python skills/uefi-ca2023/scripts/uefi_ca2023.py build C:\firmware-work\stock.bin C:\firmware-work\stock-ca2023.bin --report C:\firmware-work\stock-ca2023.json --owner-key C:\private-keys\owner.key.pem --owner-cert C:\private-keys\owner.der --certificates C:\firmware-work\microsoft --replace-platform-key
```

The reviewed implementation adds the 2023 KEK to KEK and the three 2023 CAs to db, retains earlier trust entries, replaces PK with the selected owner certificate and preserves dbx. It rebuilds signed objects, raw/GUID-defined compressed sections, complete FFS files and checksums. Old allocations become valid pad files; new files occupy verified erased space within the same volume. Unrelated file positions remain fixed.

The output has the input's length. A 16 MiB input produces 16 MiB; an 8 MiB BIOS-region input remains 8 MiB. The report records input/output hashes, owner fingerprint, exact changed byte ranges and modified allocations. Never enlarge an image by merely appending certificates beyond the flash volume. For another storage layout, implement and validate its own adapter.

## 6. Test before flashing

Require all these results:

1. Re-extraction finds exactly one active PK, KEK, db and dbx factory file. New DER fingerprints match Microsoft and the selected owner. Original retained entries and dbx match the input.
2. Auth2 bounds, signed variable metadata and cryptographic signature verification pass. Rebuild/check the enclosing CMS when the stored AMI object contains bare SignedData.
3. UEFITool/UEFIExtract parses the result. Compare input/output parser messages and investigate new errors; compare original executable hashes and descriptor/ME/NVRAM/FIT bytes.
4. Every changed byte lies within the reported old key allocations or new tail allocation. Original length and volume boundaries match.
5. For a new native-parser review, execute valid and malformed fixtures with the correct x64 ABI, pointer indirections, buffer lengths and Setup Mode state. A malformed Auth2 GUID or ESL length must fail. Passing Setup Mode parsing does not prove User Mode signer authorization. Pin harness addresses to the executable hash.

Image readback and isolated emulation remain offline evidence. Label physical POST/enrollment as pending until tested on the corresponding board.

## 7. Test enrollment and Windows separately

With an authorized, board-specific flash procedure, program and verify the candidate. Enter firmware key management and use the reviewed Setup Mode/factory-enrollment sequence. A full image can contain saved NVRAM; replacing factory files alone does not guarantee those defaults are enrolled. Confirm the intended PK and all four 2023 certificates actually appear in enrolled variables.

Boot Windows through its UEFI entry with Secure Boot enabled. Export PK/KEK/db/dbx via `Get-SecureBootUEFI`, parse their complete EFI signature lists and compare DER fingerprints and dbx policy. `Confirm-SecureBootUEFI` should return `True`. Check the active EFI system partition and selected Boot Manager's signer; a file found in a staging directory does not prove what executed.

Record Windows servicing task results, event evidence and pending reboot state. Repeat collection after reboot and compare key hashes. A registry status or disappearance of a warning alone cannot establish the certificate contents. Use [windows-verification.md](windows-verification.md) for commands and the distinction between boot acceptance and a proven active signer.

The final deliverable should say exactly which of file construction, native parsing, physical enrollment, Secure Boot enforcement and Windows servicing were verified, and which remain pending.
