# Prism SPI Flash USB Creator

A portable **Windows 10/11 x64** application with the Prism interface, real motherboard photos, an embedded firmware selector, USB Refresh, and a live preparation log. One EXE contains Python/Tk, Pillow, the DOS menu, FreeDOS, the vendor flasher, and the four exact published firmware pairs. It needs no setup, installed Python, Rufus, or runtime download. Run it from the PC's internal drive.

[Download the portable EXE or ZIP](https://github.com/BegemotX99/uefi-ca2023-agent-kit/releases/tag/prism-usb-creator-v1.0.1). This is a preview release for physical hardware testing; see the validation limits below.

**1.0.1 adds the Fudan FM25W128 (`A1 28 18`, 16 MiB) to the reviewed parts table.** This chip was missing from 1.0.0. See [the chip-support report](FM25W128.md). Existing Prism USBs can use the release's small `Prism-USB-Update-1.0.1.zip`: replace `PRISM.EXE`, `FPARTS.TXT` and `SOURCE.ZIP` together in the USB root. Formatting is unnecessary for this update. The paired DOS menu is required because it verifies the exact parts-table hash. Try **1 / Backup entire 16 MiB** first; actual chip detection and hardware read/write compatibility still need confirmation on the target board.

**This USB boots through Legacy/CSM. FreeDOS is not a native UEFI application.** A machine with only UEFI boot and no CSM cannot boot this release. Secure Boot must permit Legacy/CSM boot. The creator itself does not change firmware settings or enrolled keys.

## Included motherboards

| Selection | Exact firmware | Image size |
|---|---|---|
| HUANANZHI X99-F8 GAMING V6.0 | Published F8 V6.0 CA2023 build | 16,777,216 bytes |
| Machinist X99-MR9S | X9MRS010, stock Mi899 base + CA2023 | 16,777,216 bytes |
| Qiyida X99-H9S 001 | X9H9S001 + CA2023 | 16,777,216 bytes |
| Qiyida X99-H9S 002 | X9H9S002 + CA2023 | 16,777,216 bytes |

These are the exact modified images in [the tested BIOS catalog](../bioses/catalog.json), with no additional firmware modifications made by the USB creator. Original and modified firmware hardware tests are **maintainer-reported**, as recorded in that catalog. That evidence does not establish that this new USB creator or DOS wrapper has been tested on physical hardware.

**Prebuilt images are signed with the author's key. To manage Secure Boot yourself, build the firmware with your own key.** This EXE contains no private signing keys. Firmware factory defaults and currently enrolled Secure Boot variables are separate states; flashing alone does not guarantee factory defaults are enrolled.

## Create a USB

1. Download `Prism-USB-Creator.exe` from the Prism release and check its SHA-256 against `SHA256SUMS.txt`. The EXE is not Authenticode-signed.
2. Open it from your internal drive. Choose the **exact motherboard and revision** shown on your board. H9S001 and H9S002 are different firmware selections with the same board photograph.
3. Connect the USB and click **Refresh**. The list displays drive letters, device model, capacity and Windows disk number. Selecting it displays its serial number.
4. Click **Run as administrator**, reselect the drive if necessary, check the erase box, and click **Create bootable USB**. Type the exact `ERASE <disk number>` phrase in the final dialog. **This replaces all partitions and files on that USB.**
5. Wait for successful raw readback. Safely remove it. If no drive letter appears, reconnect the USB.
6. On the target board choose the USB boot entry **without `UEFI:`**, with Legacy/CSM available.

Supported media: USB storage reporting a unique usable serial number, 512-byte logical sectors, and 256 MiB–512 GiB capacity. The creator excludes Windows boot/system disks and refuses read-only, offline, unidentified, changed or ambiguous USB devices. It also refuses the drive hosting the running EXE. Some USB bridges report inconsistent serial numbers; those devices are conservatively refused.

The application stages a sparse temporary image, locks/dismounts existing target volumes, verifies the identity again on the open physical handle, and creates one active MBR/FAT32 partition across the usable disk. The MBR is written last; all copied data and filesystem metadata are read back. This is a quick format, not a secure erase of old data. Allow at least 512 MiB of free space on an NTFS temporary drive for the staged payload, FAT metadata and EXE extraction. The virtual image length equals USB capacity; NTFS sparse allocation avoids allocating that full length. The window has a vertical scrollbar so controls remain reachable on smaller displays.

## DOS menu

Use **1** for backup, **2** for write, **0** for DOS, or arrow keys and Enter.

- **Backup entire 16 MiB:** invokes the unmodified Intel FPT 9.1.10.1000 with `-d BACKnnnn.BIN`. It never overwrites an existing numbered backup. Only a successful return and an exact 16 MiB result are accepted. SHA-256 is saved in `BACKUPS.TXT`.
- **Write entire 16 MiB:** verifies `BIOS.BIN` against the selected build's embedded SHA-256, performs a full-chip preflight dump, then requires typed `FLASH`. It calls `FPT.EXE -f BIOS.BIN`, without `-BIOS` or force/unlock/no-verify flags. A second full 16 MiB dump must match SHA-256 before success is shown. There is no automatic reboot.
- **Exit:** returns to the FreeDOS command prompt.

The prepared USB contains the selected modified `BIOS.BIN` and full 16 MiB original `FACTORY.BIN`. **FACTORY.BIN is an original reference, not a backup of your physical board.** Use option 1 to retain that board's unique data before a full-chip write. Full images include descriptor and ME as well as the BIOS region, and can replace board-specific data. The menu does not detect or prove motherboard compatibility: the operator must match the actual board and revision to the selected image. CPU model is not used as an allowlist.

The menu pins both `FPT.EXE` and the reviewed `FPARTS.TXT`; altered tools are rejected. Version 1.0.1 appends one reviewed Fudan entry to the original vendor table; the Intel EXE is unchanged. An unsupported SPI part, inaccessible region, locked descriptor, or any FPT error stops the operation. There is no automatic fallback to a partial BIOS-region write. Preserve `FLASH.LOG` and `FPT*.LOG` if stopped. After a write error or failed readback, keep power on and preserve the logs for diagnosis. A successful preflight read does not prove write permission; FPT can still refuse a locked write.

## Validation and limits

The published build report distinguishes source tests, EXE checks, image inspection, QEMU boot and file-backed simulated flashing from physical testing. QEMU cannot validate Intel C612 SPI access or a real USB bridge. **The new Windows physical-device writer and DOS flashing menu need hardware testing.** Previously reported BIOS-image hardware passes remain scoped to those images.

See [the validation record](VALIDATION.md) for the completed checks and pending hardware tests.

The test fixture in `dos/fpt_test_stub.c` copies a local `CHIP.BIN`; it never accesses SPI. It is used only in test images with a prominent SIMULATION banner, and is not included in the production payload.

## Build from source

Use Windows x64, Python 3.12, `pip install -r usb_creator/requirements-build.txt`, and Open Watcom v2 with its DOS 16-bit compiler, headers and libraries. Download the Prism release's `Prism-Build-Inputs.zip`, check its checksum, and extract it to a new directory. This archive supplies the exact public BIOS assets, boot sectors, FreeDOS binaries/sources, vendor tool, photos and notices. It contains no private keys or personal firmware dumps.

```powershell
python usb_creator/build.py --assets C:/build-inputs/assets --watcom C:/WATCOM --work C:/build-work --output C:/prism-dist
python -m unittest discover -s tests -v
C:/prism-dist/Prism-USB-Creator.exe --self-test C:/test/report.json --image-dir C:/test/images
```

Use new work/image paths. The self-test creates ordinary local image files and never opens a physical disk. For VM integration tests, run `python usb_creator/test_dos_vm.py --help`; provide explicit QEMU, QEMU firmware, Watcom, assets and work paths. A successful file-backed test is not a hardware flash pass.

The build regenerates the C board table from the verified manifest, compiles the production DOS menu, updates its GPL/MIT source bundle, rehashes all embedded assets, then builds one windowed PyInstaller EXE. The build report records final EXE SHA-256 and the four BIOS hashes. Byte-for-byte EXE reproducibility is not promised because build timestamps and compiler/runtime versions can differ.

## Sources, photographs and third-party rights

Original Prism source is covered by the repository MIT license. Bundled firmware, photographs, FreeDOS, Intel FPT, and third-party runtimes retain their respective rights; the repository MIT license does not relicense them. Notices are embedded under `usb-assets/licenses`; FreeDOS source packages and DOS-menu source are copied to every prepared USB in `SOURCE.ZIP`.

- [HUANANZHI official X99-F8 V6.0 product page](https://www.huananzhi.com/en/list_6/640.html): F8 photograph. The manifest retains the original image URL provenance.
- [Mi899](https://github.com/miyconst/Mi899): MR9S and H9S photographs pinned to commit `b278162a158c53eb4849e49032428f26bf88795e`. Photos identify the selection visually; inspect the physical PCB revision yourself.
- [FreeDOS](https://www.freedos.org/): FreeDOS 1.4 kernel and FreeCOM, with matching source archives in `SOURCE.ZIP`.
- [Open Watcom v2](https://github.com/open-watcom/open-watcom-v2): compiler; this build used `ow-snapshot.tar.xz` SHA-256 `ebe7db36bc43eabd3c4de0e67f0897ab3a7261253f494dafbca1a116018f7e82`.
- Intel FPT 9.1.10.1000: unmodified DOS utility from the supplied F8 stock firmware kit; Intel proprietary software, not Prism source. Its parts table retains all original rows and appends the documented FM25W128 entry.

`KERNEL.SYS` SHA-256: `932c0c155701eddb7b902f7269a1b2ce31f5c82a6dc195172f2336d18a74e1fb`.
`COMMAND.COM` SHA-256: `077808379e896476f7f69d62e6c8989d8fc23e8ef58d1c8492db1ac106784107`.
The 440-byte MBR code and FAT32 VBR template are pinned by the embedded manifest. Disk-specific BPB and partition fields are constructed by `core.py`; FreeDOS boot code is retained.
