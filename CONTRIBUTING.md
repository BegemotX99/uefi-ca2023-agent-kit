# Contributing an additional motherboard or firmware build

Submit a report with board model/revision, input origin and hash, image geometry, active factory defaults and native enrollment path. Provide tooling versions and reproducible commands. Obtain firmware redistribution rights before attaching a binary or a dump containing persistent state.

A new entry in `reviewed-images.json` needs the full image SHA-256, BIOS-region SHA-256, native driver hashes, validity of all FFS files, one factory key set, original list hashes, verified available space and FIT review. Explain whether the native routine expects Auth2, another wrapper or plain ESL.

For changed enrollment drivers, document the decompressed executable comparison and the relevant native routine contracts. Exercise valid KEK/db payloads and negative inputs. Verify detached signatures independently. Report the emulated mode and exactly which checks it covers. Record physical POST, key enrollment and Windows state separately if available.

For a builder change, add a regression case that catches a concrete malformed input or behavioral failure. Run the unit suite. Keep signed binaries, private keys, personal variables, and proprietary firmware dumps outside the source tree. CI runs synthetic parsing/signing cases without motherboard images.

New vendor layouts should enter through a reviewed adapter with explicit eligibility. Preserve unsupported input as inspection-only until the missing checks exist. Explain capsule authentication and verified boot coverage where applicable.
