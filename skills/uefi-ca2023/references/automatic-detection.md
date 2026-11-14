# Automatic detection without a profile for every BIOS

## How it works

The whole-image SHA-256 is recorded for provenance, but it is no longer the patch eligibility gate. The tool discovers the SPI BIOS region, FIT, firmware volumes, factory key files, native drivers and erased tail from each input. No motherboard name or key-file offset is supplied by a per-board profile.

The same supported enrollment code can appear in many board images. `enrollment-families.json` records complete reviewed three-driver fingerprint sets and the format contract they implement. A match allows use of that contract on another whole-image hash. `reviewed-images.json` remains a historical artifact index; adding an image there does not enable patching.

Fingerprint recognition is deliberately exact, including FFS packaging. Different compression or metadata can therefore cause a conservative refusal even when executable behavior is unchanged. Such a case needs a family review. There is no similarity score or force option that converts unfamiliar code into a proven parser implementation.

## Eligibility checks retained

- Raw power-of-two image geometry and a valid Intel BIOS region when a descriptor is present; unsupported capsules require extraction/review.
- Valid FIT location and size; selected boot-policy/key-manifest FIT records stop the operation.
- Exactly one readable PK/KEK/db/dbx factory set in one supported AMI FFS2 volume with the reviewed volume GUID and erase polarity.
- Full FFS enumeration, checksums and genuinely erased tail space, with native drivers active and each required driver present exactly once.
- One reviewed complete native enrollment-driver family, preserving its exact three fingerprints. Matching one driver alone is insufficient.
- The original factory PK, KEK, db and dbx payload hashes must match the existing reviewed AMI test-key baseline. This protects the prior key-policy assumptions; custom or other OEM defaults remain inspection-only.
- Explicit owner-PK replacement, matching encrypted local owner key/certificate, certificate validity and all four pinned Microsoft DER objects.
- Auth2 signing and OpenSSL verification, compression readback, final key/list readback, unique active defaults and valid final checksums.
- Sufficient space for the actual signed replacements, unchanged unrelated bytes and files, original length/volume map, retained old KEK/db entries and identical dbx.
- Successful independent UEFIExtract parsing before either deliverable is saved, with identical input/output diagnostics. Preexisting vendor diagnostics are not a clean bill of health. Any difference conservatively stops the build.

The FIT test detects selected structures rather than establishing universal absence of authenticated boot. The adapter covers the documented AMI factory-key path. Full boot policy and physical board compatibility remain separate review/test obligations.

## Commands

```powershell
python skills/uefi-ca2023/scripts/uefi_ca2023.py inspect C:\firmware-work\stock.bin
```

Read `automatic_patch.status`: `eligible` means all layout/family preflight checks passed, while `inspection-only` includes the blocking reason. Eligible does not mean flashed, boot-tested or Microsoft-certified. The build command remains the same, with UEFIExtract now required:

```powershell
python skills/uefi-ca2023/scripts/uefi_ca2023.py build C:\firmware-work\stock.bin C:\firmware-work\new.bin --report C:\firmware-work\new.json --owner-key C:\private-keys\owner.key.pem --owner-cert C:\private-keys\owner.der --certificates C:\firmware-work\microsoft --replace-platform-key --uefiextract C:\tools\UEFIExtract.exe
```

The saved report contains `eligibility`, the native family/fingerprints, optional historical image identity, exact changed ranges, owner fingerprint and independent parser result. Unknown code, another key baseline, missing/ambiguous defaults, new diagnostics or insufficient space produces no firmware deliverable. There is no per-BIOS profile to add for a matching family.

## Adding support once per implementation

When a driver set or storage contract differs, review it using [board-review.md](board-review.md). Record valid and malformed native parser tests and the factory lookup/enrollment behavior. Add a family or adapter only when those results justify it. Other boards with that same implementation can then be recognized without new whole-image profiles. Arbitrary motherboard firmware cannot be safely patched solely because a certificate GUID or a run of FF bytes was found.
