# Third-party provenance

The AMI FFS parsing and certificate checks are adapted from the user's PLATON/X99 project in `tools/x99-secureboot/x99_sb2023.py`. This publication contains independently reusable Python source and documentation from that work. At the maintainer's explicit request, four tested original/modified firmware pairs are now distributed separately as GitHub release assets; their identities, source provenance and test reports appear in [the BIOS catalog](bioses/README.md). The source repository's MIT license does not relicense motherboard-vendor firmware, AMI, Intel or Microsoft components. Those retain their applicable third-party rights and terms. Distribution here supplies neither manufacturer endorsement nor universal board compatibility.

Microsoft certificates retain their issuer identity and applicable distribution terms. Obtain them from [Microsoft Secure Boot objects](https://github.com/microsoft/secureboot_objects). That project publishes its own license. This repository records fingerprints and download guidance.

OpenSSL, Python, cryptography, UEFITool, and any emulator retain their respective licenses. Install them separately. Their executables and third-party source trees are outside this distribution.

Memtest86+ and the AMI menu integration are adjacent project work. This repository's certificate workflow needs neither Memtest86+ nor its binaries. For that separate feature, review upstream GPL source and distribution obligations. [Memtest86+ source](https://github.com/memtest86plus/memtest86plus)
