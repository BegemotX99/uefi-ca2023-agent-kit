# Evidence required for an additional board or build

Record board model/revision, firmware source, full input hash, BIOS-region hash, build identity and image geometry. Identify the active factory files and enrollment sequence, all original list hashes, driver FFS and extracted executable hashes, valid checksums, erased-space bounds and any authenticated boot structures.

For different enrollment drivers, compare extracted executable code and establish the precise native reader contract. Test valid payloads and malformed wrappers/list lengths. Pin emulation offsets, mode, ABI and results to the executable hash. Independently verify signatures. Report physical POST, enrollment, enforcement and Windows servicing separately.

The supplied adapter assumes the reviewed AMI storage layout and original list hashes. A firmware with another baseline needs an adapter that expresses its actual invariants, rather than a new hash inserted into the existing manifest. Document User Mode authorization requirements and any capsule or verified-boot coverage.

Record tooling versions and reproducible commands. Add regression tests for concrete new behavior or malformed inputs. Keep private signing keys, personal NVRAM and firmware dumps outside source packages. Firmware redistribution requires the appropriate rights.
