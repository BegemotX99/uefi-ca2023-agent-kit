# UEFI CA 2023 Agent Kit

Firmware engineering instructions and portable tools for adding Microsoft Secure Boot 2023 certificates to reviewed AMI X99 firmware. The repository includes a report of the original work, a skill for Codex and Claude Code, and an offline image inspector and builder.

Start by asking your agent to read this repository's `AGENTS.md` and `skills/uefi-ca2023/SKILL.md`, inspect your supplied firmware, and report the detected layout and eligibility. An agent with repository access can follow these instructions directly. Installation enables automatic skill discovery in supported clients.

## What you get

- [Four hardware-tested original/modified BIOS pairs](bioses/README.md), published as full 16 MiB release ZIPs. The maintainer confirmed successful tests of both images for F8 V6.0, MR9S, H9S001 and H9S002 on 14 November 2026.
- A standard-library Python inspector for Intel SPI maps, directly visible AMI FFS volumes, compressed factory key files, and pinned Microsoft certificate fingerprints.
- An automatic builder for the supported AMI layout and four reviewed enrollment-driver families. Different whole-image hashes, motherboard names and discovered volume offsets do not require individual profiles. Unknown native code and unsupported layouts remain inspection-only.
- Fresh encrypted owner-key generation on your own machine.
- Technical instructions for new boards, Auth2 signatures, FFS placement, enrollment, Windows verification, and manual hex editing.
- Public owner certificates from earlier Qiyida and Machinist builds, with their SHA-256 fingerprints and provenance.

The tools operate on files. A physical firmware flash needs its own exact target, flashing procedure, recovery plan, and user authorization. A malformed image can prevent the motherboard from starting.

## Quick start

Python 3.11 or newer is required. Inspection uses Python's standard library. Building and key generation also require `cryptography` and OpenSSL on PATH. Every build requires trusted UEFIExtract on PATH or its path supplied through `--uefiextract`. On Windows, choose an OpenSSL distribution you trust. On Linux, use the distribution package manager.

```sh
git clone https://github.com/BegemotX99/uefi-ca2023-agent-kit.git
cd uefi-ca2023-agent-kit
python skills/uefi-ca2023/scripts/uefi_ca2023.py inspect /path/to/stock.bin
python -m pip install -r requirements-build.txt
openssl version
```

Use paths outside the checkout for key material. The parent directories must already exist. The key generator prompts twice for a password and writes an encrypted PKCS#8 PEM private key and a public DER certificate.

```sh
python skills/uefi-ca2023/scripts/uefi_ca2023.py keygen --name "My MR9S Secure Boot Owner" --key /private/location/owner.key.pem --cert /private/location/owner.der
```

Download the four public Microsoft DER certificates using the links in the [certificate guide](skills/uefi-ca2023/references/certificates-and-signing.md). Put them in a local directory. The builder checks the pinned fingerprints regardless of their filenames.

```sh
python skills/uefi-ca2023/scripts/uefi_ca2023.py build /path/to/stock.bin /path/to/new.bin --report /path/to/new-report.json --owner-key /private/location/owner.key.pem --owner-cert /private/location/owner.der --certificates /path/to/microsoft-der-directory --replace-platform-key
```

The `inspect` result includes `automatic_patch.status`, a matched enrollment family or a specific refusal reason, discovered volume bounds and available erased tail. Layout eligibility is a preflight result; final capacity, signing and output validation remain build-time checks. See [automatic detection](skills/uefi-ca2023/references/automatic-detection.md).

This builder replaces the reviewed AMI test PK with your public owner certificate, retains the original 2011 KEK/db entries, adds all four Microsoft 2023 certificates, and preserves the factory dbx. It prompts for the encrypted key password. It checks signatures with OpenSSL, checks the final firmware inventory and payloads, requires successful UEFIExtract parsing with identical input/output diagnostics, and saves a new image of the original length with a JSON report. Each fresh signature can produce a different compressed length and output hash.

When preserving an existing OEM PK is a requirement, use the policy paths described in the [signing guide](skills/uefi-ca2023/references/certificates-and-signing.md). The included builder implements the explicit owner-PK migration workflow.

## Install the skill

Copy the entire `skills/uefi-ca2023` folder, including `references`, `scripts`, and `agents`, to the appropriate directory. Keep all files together.

| Client | Project installation | Personal installation | Explicit invocation |
|---|---|---|---|
| Codex | `.agents/skills/uefi-ca2023/` | `~/.agents/skills/uefi-ca2023/` | `$uefi-ca2023` |
| Claude Code | `.claude/skills/uefi-ca2023/` | `~/.claude/skills/uefi-ca2023/` | `/uefi-ca2023` |

Client versions and organization policies can change skill discovery. Consult the installed client's documentation if a skill fails to appear. Claude web and ChatGPT interfaces need their own supported skill-upload or tool-access mechanism. A repository URL by itself provides context only to an agent capable of fetching it. [Codex skills](https://developers.openai.com/codex/skills) · [Claude Code skills](https://code.claude.com/docs/en/skills)

Example request after installing or reading the repository:

> Use the uefi-ca2023 skill on my attached stock BIOS. Identify the board and image hash, inspect factory PK/KEK/db/dbx, and determine whether the native enrollment code accepts the new payloads. Build a new image only after the required review passes. Provide the full image, hashes, exact changed ranges, enrollment steps, and honest validation status. Use my own owner keys. Keep hardware flashing as a separate action.

## Documentation

- [Complete start-to-finish guide: original Microsoft downloads, PC tools, signing, integration and testing](skills/uefi-ca2023/references/end-to-end-guide.md)
- [Automatic layout detection, eligibility and retained checks](skills/uefi-ca2023/references/automatic-detection.md)
- [Project report and validation history](docs/REPORT.md)
- [Skill entry point](skills/uefi-ca2023/SKILL.md)
- [Firmware layout and new-board review](skills/uefi-ca2023/references/firmware-workflow.md)
- [Certificates, signatures, and key ownership](skills/uefi-ca2023/references/certificates-and-signing.md)
- [Post-flash enrollment and Windows checks](skills/uefi-ca2023/references/windows-verification.md)
- [Manual hex-editor procedure](skills/uefi-ca2023/references/hex-editor.md)
- [Troubleshooting observed failures](skills/uefi-ca2023/references/troubleshooting.md)
- [Machine-readable reviewed images](skills/uefi-ca2023/references/reviewed-images.json)
- [Public owner certificate policy](public-owner-certificates/README.md)
- [Contributing a board review](CONTRIBUTING.md)

## Supported scope

Inspection covers factory files that the parser understands. Missing results require deeper extraction and review. The builder identifies supported storage and native enrollment code independently of whole-image identity. It retains the original reviewed factory key baseline. Another PK or trust baseline, different enrollment code, nested/capsule storage or ambiguous copies needs review of that format or family. A board name, familiar GUID, or a matching CPU alone cannot establish compatibility.

Historical evidence applies to each recorded artifact. A successful emulated parser call establishes that routine's behavior for its supplied arguments. Physical POST, enrollment, Secure Boot enforcement, and Windows servicing require hardware evidence. This publication's rebuilt artifacts have offline validation only.

Original repository code and documentation are available under MIT. Firmware ownership, Microsoft public objects, and third-party tools retain their own licenses. See [third-party notices](THIRD_PARTY.md).
