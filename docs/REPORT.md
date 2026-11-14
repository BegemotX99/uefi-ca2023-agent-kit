# Secure Boot CA 2023 implementation report

Prepared 14 November 2026 from the PLATON/X99 project artifacts and conversation. The original task evolved from a HUANANZHI F8 dashboard to stock-firmware certificate migration on multiple X99 boards. This repository captures the certificate engineering workflow and supporting evidence.

## The implemented migration

The reviewed AMI firmwares shipped factory PK/KEK/db/dbx files containing an AMI test PK and 2011-era Microsoft trust entries. The project added Microsoft Corporation KEK 2K CA 2023 to KEK and Windows UEFI CA 2023, Microsoft UEFI CA 2023 and Microsoft Option ROM UEFI CA 2023 to db. These certificate fingerprints appear in the skill references and machine-readable JSON.

The owner-key migration replaced the AMI test PK with a dedicated project-owner public certificate. New PK/KEK/db lists were packaged in owner-signed Auth2 objects. The native AMI setup code locates the relocated factory files by GUID. The implementation filled retired allocations with valid pads and appended complete new FFS files in erased volume space. The original dbx and unrelated executable modules stayed byte-identical for the certificate-only variants.

This addresses the firmware's built-in default trust set. Enrolling that set, selecting a compatible signed Windows Boot Manager, and completing Windows servicing remain distinct steps. The original work observed a Windows InProgress status and a warning on one board even after firmware defaults had been changed. Final Windows status needs task/event and enrolled-variable evidence.

## Recorded inputs

| Board/build | Full 16 MiB input SHA-256 | Evidence |
|---|---|---|
| HUANANZHI X99-F8 V6.0 | `69a8c5e848a440667d8d83820812735e26bf143ce0e6a2312e22f0fa2b9f5734` | Prior project profile records hardware-tested migration. Conversation reports success. Publication rebuilds require their own test. |
| Qiyida H9S X9H9S001, archive stock | `39ded021001560cf0adc7acf0b034d019e640d601a96bfffe2c611f7c1350fbb` | Offline image, signature and native parser evidence recorded. |
| Qiyida H9S X9H9S002, November dump | `f5a9b5ca654fe5c9b280a8b7d09139ec092773f64cf855c4c1596c086f1cb1c3` | Native DXE/SMM Setup Mode accepted new KEK/db and rejected malformed objects. Physical board test pending. |
| Machinist MR9S X9MRS010, Mi899 stock | `a85922196ec5f910fb9d258934d7bd0e113b00263bd2da1a450b5f538342e350` | Native DXE/SMM and structural checks recorded. Physical board test pending. |

`reviewed-images.json` additionally pins BIOS-region hashes and each native enrollment-driver FFS hash. Historical output hashes identify the original project artifacts only. Fresh owner keys and signing timestamps create different output hashes.

## Comparison findings

H9S001 and H9S002 were different executable builds. They shared factory certificate contents. The 002 SecureBootDXE PE differed only in timestamp bytes, while the NVRAM driver binaries also changed elsewhere. Many PEI file differences disappeared after accounting for changed load addresses. The July and November H9S002 dumps matched everywhere outside the two saved NVRAM volumes.

The supplied MR9S dump had SHA-256 `31025552b9aaaf738b719179d2ba760fc5676ab7a167014f05c4dbe6367fc649`. It identified as X9MRS010 dated 21 February 2025. Two compressed file containers failed to decompress. The Mi899 stock and independently downloaded public v6.2 dump matched byte-for-byte and provided functioning compressed containers. The user's subsequent instruction selected the complete Mi899 image as the base, which became the source for the later CA 2023 and Memtest variant.

The Mi899 stock archive was pinned at Git tree `b278162a158c53eb4849e49032428f26bf88795e`, archive blob `4fa4c3a807a89a48bfb47e1d8c2c6cdfd432243e`. The lookup found X9MRS010 as that repository's stock version. This is a time-specific source observation. [Mi899 BIOS directory](https://github.com/miyconst/Mi899/tree/master/src/Mi899.Data/Bioses)

## Historical artifacts

| Artifact | Full image SHA-256 | Test scope |
|---|---|---|
| H9S002 CA 2023 | `69a3d3ce636440680c9c6c76190f59973ddd709bc60268bd065b32bc2e7a3f82` | Offline signature, image and native KEK/db parser checks. |
| MR9S supplied dump with two repairs and CA 2023 | `a8b44de94e6a0c015b727c5b98b2d7d344b84a563599650471bc9185c34d4309` | Offline checks, with repair scope explicitly recorded. |
| Exact Mi899 MR9S stock plus CA 2023 baseline | `d5048d8828fe168544933e9a13f22bc10a6037f3d5fcdc445b62275c5bcf210f` | Byte identity outside certificate allocations verified. |
| Mi899 MR9S plus CA 2023 and AMI Memtest menu | `d6d36024a31c932933d7e3b0d5c4bc28ccd9d92429fc6ed8cd3f19cc7ed48366` | Native form/control extraction and isolated callback/loader emulation. Physical menu and Secure Boot launch pending. |

The firmware binaries, original dumps, signing private keys and personal Windows logs remain outside this public repository. Public PK certificates and their fingerprints are included for provenance.

## Limits and publication decisions

The cross-board workflow describes how to establish compatibility. The public builder accepts four reviewed inputs and matching 8 MiB BIOS regions. It requires local owner keys, explicit PK replacement, pinned Microsoft DER objects and OpenSSL signature verification. The public inspector covers directly visible AMI FFS default files and reports unsupported or ambiguous parsing. Broader compatibility needs new adapters and evidence.

The project record does not provide physical enrollment success for the H9S and MR9S candidates. The F8's USB Memory Lab hardware pass applies to that USB artifact and supplies no physical evidence for another firmware image. Firmware modification and image construction do not confer Microsoft certification or complete Windows servicing automatically.

## Public-key publishing

The user requested reusable agent instructions and asked about publishing owner keys. The publication includes the public Qiyida and MR9S certificates, their subjects and fingerprints, plus a fresh encrypted key generator. The public files let an independent user identify the prior signing owner. A new user retains control by generating their own pair. A shared maintainer PK requires an explicit custody and update policy.

The repository uses MIT for original code and documentation. Third-party firmware and certificate provenance are described separately. This public-source and public-key release was requested by the user in the project conversation.

## Publication validation on 14 November 2026

- Six synthetic regression tests passed, including Auth2 signing/verification, malformed ESL rejection, FFS compression/checksums, unknown-image refusal, output overwrite protection and public certificate fingerprints.
- The skill passed the skill-creator schema validator.
- All four reviewed full images and their matching BIOS regions completed fresh builds: eight offline cases. An ephemeral encrypted RSA-3072 owner identity was used only inside a temporary directory. Each case read back PK/KEK/db/dbx entry counts of 1/2/5/77 and all four Microsoft 2023 fingerprints. Signature and changed-range/layout checks passed.
- Official UEFIExtract NE A76 parsed each input and output. The tool exited successfully and emitted identical diagnostics for each pair. This comparison establishes no new reported diagnostics; it does not assert that vendor stock images have no preexisting diagnostics.
- Microsoft's four original DER files at upstream commit `3d762aecbaecd12402efd21ba89c8c7bd40da4bd` were downloaded independently and matched the pinned fingerprints.

The temporary test keys and candidate firmware images were discarded after the checks. These tests do not add physical motherboard, enrollment or Windows-servicing evidence for the new builds. CI runs the synthetic tests; the real-image tests require local firmware inputs that are deliberately excluded from the public repository.
