# Hardware-tested original and CA 2023-modified BIOS pairs

The maintainer confirmed on **14 November 2026** that both the original and modified BIOS were tested successfully on each of these four boards. These are **user-reported hardware passes**, supplemented by offline file, certificate and preservation checks. Publication does not claim an independent hardware rerun or testing of every firmware feature.

[Download the GitHub release](https://github.com/BegemotX99/uefi-ca2023-agent-kit/releases/tag/tested-bios-2026-11-14).

| Exact board/build | Original + modified full 16 MiB ZIP | Test status |
|---|---|---|
| HUANANZHI X99-F8 GAMING V6.0 | [F8 V6.0 CA 2023](https://github.com/BegemotX99/uefi-ca2023-agent-kit/releases/download/tested-bios-2026-11-14/huananzhi-f8-v60-ca2023.zip) | Original and modified: hardware-tested, maintainer-reported pass |
| Machinist X99-MR9S X9MRS010, Mi899 stock base | [MR9S CA 2023](https://github.com/BegemotX99/uefi-ca2023-agent-kit/releases/download/tested-bios-2026-11-14/machinist-mr9s-mi899-ca2023.zip) | Original and modified: hardware-tested, maintainer-reported pass |
| Qiyida X99 H9S X9H9S001 | [H9S001 CA 2023](https://github.com/BegemotX99/uefi-ca2023-agent-kit/releases/download/tested-bios-2026-11-14/qiyida-h9s-001-ca2023.zip) | Original and modified: hardware-tested, maintainer-reported pass |
| Qiyida X99 H9S X9H9S002, November source image | [H9S002 CA 2023](https://github.com/BegemotX99/uefi-ca2023-agent-kit/releases/download/tested-bios-2026-11-14/qiyida-h9s-002-ca2023.zip) | Original and modified: hardware-tested, maintainer-reported pass |

Each ZIP contains `ORIGINAL-16MiB.bin`, `MODIFIED-16MiB.bin`, the public platform-key certificate, `MANIFEST.json`, `SHA256SUMS.txt` and a README. Historical verification reports are included where applicable, prefaced to explain that their old physical-test-pending wording predates the new confirmation. The [catalog](catalog.json) records every image and archive hash, source, scope, key policy and validation evidence.

The modified images are the historical CA 2023-only candidates, preserved byte-for-byte. They replace the AMI test PK with the project owner's public certificate, retain earlier KEK/db trust entries, add the Microsoft 2023 KEK and three 2023 db certificates, and preserve dbx. They add no dashboard, PLATON or Memtest menu. The maintainer retains private signing keys; none are distributed. Use the source toolkit with your own owner keys if you want personal update authority.

The full images preserve their original source descriptor, Intel ME and saved NVRAM/platform state. Match the exact motherboard and revision and review the source image's applicability to your board before flashing. The ZIPs contain full SPI images, not generic updates for every similarly named X99 board. Firmware enrollment and Windows verification remain separate from writing the image.

This release contains **only these four tested pairs**. MR9A, legacy F8 db-only, repaired personal MR9S dumps and the MR9S Memtest variant are excluded. An image rebuilt with fresh keys or another firmware base needs its own testing; these results do not transfer automatically.

Original/vendor firmware and included third-party components retain their respective rights and terms. The repository's MIT license covers original project code and documentation and does not relicense AMI, Intel, vendor firmware or Microsoft certificates. Provenance is recorded in the catalog and [third-party notices](../THIRD_PARTY.md).
