# Portable Windows auto-detect patcher

[Download the complete Windows x64 ZIP](https://github.com/BegemotX99/uefi-ca2023-agent-kit/releases/tag/portable-windows-v1.0.0).

Extract the entire ZIP, keep `_internal` beside `UEFI-CA2023-AutoDetect.exe`, and run the EXE. It needs no Python, pip, OpenSSL or UEFIExtract installation and makes no runtime downloads. Windows 10/11 x64 is the target; the packaged application was tested on Windows 11 x64.

The GUI keeps **Open**, **Analyse**, **Save As** and a live analysis log. Open selects a stock BIN/ROM. Analyse discovers the layout, reports eligibility and prepares a candidate only when the checks pass. Save As remains disabled until the full candidate is verified. It writes a new image plus `.report.json` and `.log.txt`, verifies readback, refuses existing destinations and preserves the original.

The owner-key controls create a fresh encrypted local key pair or load an existing encrypted PEM and public DER. Confirm the owner-PK replacement checkbox before preparation. The private-key password is used locally during signing and is not logged. No private signing identity, motherboard image or personal report is bundled. Refer to [START-HERE instructions](README.txt).

## Validation retained

The GUI calls the same auto-detect backend as the source CLI. It retains the native family fingerprints, original factory-key baseline, descriptor/FIT/FFS checks, erased-space bounds, certificate pins, owner-key matching, Auth2 signing/OpenSSL verification, compression and payload readback, unique defaults, unchanged dbx and unrelated-byte checks. Successful UEFIExtract parsing with matching input/output diagnostics is mandatory. Unknown implementations remain inspection-only; no force override is added.

Every runtime dependency is in the ZIP: Python/Tk, cryptography, native OpenSSL with its DLLs, UEFIExtract, the four original Microsoft DER certificates, family metadata and license notices. The packaged resources are hash-checked at startup. The native import audit and runtime tests exercise the dependency closure. This is an EXE plus dependency folder in one ZIP, not a single-file EXE or installer.

The Windows EXE has no Authenticode publisher signature. The release includes its ZIP SHA-256 and build report. Signed firmware update objects and an Authenticode-signed Windows executable are separate matters.

## Tested before publication

- 21 source regression tests passed, including save protection, changed-input/candidate refusal and rollback of partial saves.
- The final ZIP was extracted to another directory with a space in its path. Tests removed Python/Tcl/OpenSSL environment overrides and restricted PATH to Windows directories. They ran the extracted EXE, rather than the source Python script.
- The packaged runtime created the Tk interface, ran bundled OpenSSL/UEFIExtract, checked all four Microsoft certificate fingerprints, generated an ephemeral encrypted RSA owner key and verified Auth2 signing.
- Complete frozen-EXE builds and save/readback passed for F8, H9S001, H9S002 and Mi899 MR9S originals. MR9A and ZX inputs stayed inspection-only with no candidate saved. Corruption of a bundled certificate was refused at startup.
- The real Tk button handlers were exercised through owner-key creation, Open, background Analyse with logging, Save and unsupported-image refusal. These were automated handler tests, not a claim of manual visual QA.

The test firmware used discarded ephemeral keys and was kept outside the distributed ZIP. New local-key builds still need their own physical/enrollment/Windows checks; the historical tested BIOS assets remain separate.

## Rebuild from source

Use Windows x64, Python with working Tk, `windows/requirements-build.txt`, native x64 OpenSSL, UEFIExtract NE A76 and the four pinned DER files. The build helper acquires license notices from the listed upstream sources; runtime use is offline.

```powershell
python -m pip install -r windows/requirements-build.txt
python windows/build_portable.py --work-dir C:\build\ca2023 --openssl-dir C:\tools\openssl --openssl-license C:\tools\openssl\LICENSE.txt --uefiextract C:\tools\UEFIExtract.exe --certificates-dir C:\certificates
```

The builder pins the tested PyInstaller version, records actual dependency versions/hashes, audits native imports and creates the final ZIP with checksums. The supplied Tcl/Tk license notices correspond to the tested 8.6.12 runtime; review notices if rebuilding with a different runtime. For packaged verification, run the EXE with `--self-test C:\path\report.json`. The optional `--image INPUT --test-dir OUTPUT` mode uses ephemeral keys for offline test candidates, not release firmware.
