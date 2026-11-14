# Evidence required for an additional board or build

Record board model/revision, firmware source, full input hash, BIOS-region hash, build identity and image geometry. Identify the active factory files and enrollment sequence, all original list hashes, driver FFS and extracted executable hashes, valid checksums, erased-space bounds and any authenticated boot structures.

For different enrollment drivers, compare extracted executable code and establish the precise native reader contract. Test valid payloads and malformed wrappers/list lengths. Pin emulation offsets, mode, ABI and results to the executable hash. Independently verify signatures. Report physical POST, enrollment, enforcement and Windows servicing separately.

The supplied adapter detects the reviewed AMI storage layout and requires the original list hashes. Firmware with matching native-driver family and baseline needs no whole-image profile. Another baseline needs an adapter that expresses its actual invariants, rather than a new hash inserted into an image manifest. Document User Mode authorization requirements and any capsule or verified-boot coverage. New native implementations belong in the family registry with the evidence above.

Record tooling versions and reproducible commands. Add regression tests for concrete new behavior or malformed inputs. Keep private signing keys, personal NVRAM and firmware dumps outside source packages. Firmware redistribution requires the appropriate rights.
