# Prism 1.0.0 preview validation

Recorded 14 November 2026 on Windows 11 x64. This report covers the new USB creator and DOS wrapper. The embedded BIOSes are unchanged public release assets; their original/modified hardware passes are separately recorded as maintainer-reported in `bioses/catalog.json`.

| Check | Result |
|---|---|
| Repository tests | 27 passed, no skips, including OpenSSL Auth2 verification |
| Target protection | USB-only inventory, boot/system/read-only/offline/sector/serial guards; changed identity refused before mutation; opened device descriptor rechecked |
| FAT32 | Capacity boundaries, 8.3 names, directory cluster fields, matching FAT copies, active MBR partition and nonzero matching disk/volume identifier |
| Raw writer | File-backed write/readback; deliberate readback corruption refused; no physical device used |
| GUI workflow | No implicit final-drive selection; erase approval reset; incorrect phrase cancels; selected MR9S image reaches file-only preparation worker; success resets approval |
| Portable EXE | GUI and four photos load, all embedded hashes checked, four complete image builds with Windows-only PATH and Python/Tcl/OpenSSL environment overrides removed |
| Independent image reader | PyFatFS read every payload file in all four generated images; separately confirmed GUI-selected MR9S payload |
| Production USB boot | Final production disk image boots from QEMU USB storage directly into the Prism menu |
| DOS SHA-256 | Known `abc` vector; full 16 MiB selected-image and backup digests matched Python reference hashes |
| DOS backup | Two new numbered full 16 MiB backups; exact byte contents and digests checked |
| DOS cancellation | Empty confirmation cancels and preserves simulated chip bytes |
| DOS write | File-backed simulated full 16 MiB write followed by full-chip dump and matching SHA-256 |
| DOS readback failure | Deliberately corrupted simulated chip causes failure, never a success message |
| Tool failures | Fixture exit 99 propagated; bundled real Intel FPT started in FreeDOS and its unsupported QEMU-platform error was correctly propagated |
| Desktop visual review | Not completed: Computer Use app approval timed out. Automated GUI construction and handler checks passed; DOS screenshots were visually inspected |
| Physical USB preparation | Pending; no connected USB formatted during development |
| Physical SPI flashing with this menu | Pending; QEMU cannot validate C612 SPI access or chip/descriptor write permissions |

The simulation fixture is excluded from production assets. Production `PRISM.EXE` is compiled with `PRISM_SIMULATION=0` and pins the genuine vendor FPT and parts-table hashes. The build ZIP carries all asset hashes, and `BUILD-REPORT.json` in the release carries the exact EXE hash, BIOS catalog and verification reports.

The app uses fresh disk/volume identifiers for each USB creation to avoid deliberately cloning the same Windows disk signature onto every USB. FreeDOS boot code is retained while partition and FAT32 metadata are generated for the selected capacity.

This is a **preview for hardware testing**, not a claim of universal motherboard, USB-controller or flash-part compatibility. Review the exact board/revision before using a full-chip image. Unsupported SPI access stops without force/unlock flags. The manual and release report distinguish BIOS-image evidence from this tool's test coverage.
