# Contributing an additional motherboard or firmware build

Submit a report with board model/revision, input origin and hash, image geometry, active factory defaults and native enrollment path. Provide tooling versions and reproducible commands. Obtain firmware redistribution rights before attaching a binary or a dump containing persistent state.

Matching supported families need no new image entry. To add an implementation to `enrollment-families.json`, provide full input/BIOS-region SHA-256 evidence, the complete native driver fingerprint set, validity of all FFS files, one factory key set, original list hashes, verified available space and FIT review. Explain whether the native routine expects Auth2, another wrapper or plain ESL. `reviewed-images.json` is an optional history index, never an authorization gate. Another factory trust baseline needs a separately reviewed policy adapter; its hashes cannot merely replace the current constants.

For changed enrollment drivers, document the decompressed executable comparison and the relevant native routine contracts. Exercise valid KEK/db payloads and negative inputs. Verify detached signatures independently. Report the emulated mode and exactly which checks it covers. Record physical POST, key enrollment and Windows state separately if available.

For a builder change, add a regression case that catches a concrete malformed input or behavioral failure. Run the unit suite. Keep signed binaries, private keys, personal variables, and proprietary firmware dumps outside the source tree. CI runs synthetic parsing/signing cases without motherboard images.

New vendor layouts should enter through a reviewed adapter with explicit eligibility. Preserve unsupported input as inspection-only until the missing checks exist. Explain capsule authentication and verified boot coverage where applicable.
