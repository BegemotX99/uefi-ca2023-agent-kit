# Failures observed during the project

| Observation | Engineering response |
|---|---|
| AMI enrollment driver hashes differ | Decompress and compare the native path, then exercise the relevant parser. Keep the new input outside automatic write eligibility until evidence supports it. |
| No factory keys detected | Inspect nesting, unknown GUIDs, raw default stores, and executable resources. Report parser coverage explicitly. |
| Multiple key sets found | Identify active and recovery copies and trace the real factory enrollment path. |
| Replacement db or KEK outgrows its allocation | Relocate complete FFS objects into verified volume tail space after proving GUID-based lookup, then fill retired slots with valid pad files. |
| Auth2 object rejected | Check variable name, vendor GUID, attributes, timestamp, certificate type, signature and bare SignedData versus ContentInfo packaging. Compare native ABI arguments during emulation. |
| Factory files contain CA 2023 but Windows does not | Inspect enrolled variables and authorized factory enrollment. |
| Windows says InProgress or shows a yellow warning | Inspect servicing task, cumulative update, pending restart and TPM-WMI events. Avoid inventing success from a single registry field. |
| Secure Boot Violation screen | Record the selected boot image and its signer, enrolled db/dbx and any revocation conflict. An example image of a violation screen alone establishes no actual board failure. |
| Compressed files fail to decompress | Check extraction coverage and native format. Compare an independently sourced, exact-build donor before concluding damage. Any repaired bytes are a separate documented change. |

The supplied Machinist dump and Mi899 stock shared `X9MRS010`, but two compressed containers differed. The supplied version failed decompression. Mi899 stock matched another public v6.2 reference byte-for-byte. A repair experiment restored those two containers while preserving the supplied dump's saved variables and ME data. A later user request required the complete Mi899 stock as the base, so that variant starts from Mi899's own bytes throughout.

Full SPI images contain persistent board state as well as executable firmware. Two files with matching executable modules can differ in NVRAM, counters, configuration and platform data. Describe whether a comparison used raw offsets, FFS identities, decoded payloads, executable sections after relocation handling, or live hardware observations.

Prism graphics, Memory LAB, Memtest86+, UI launch hooks, GPU compatibility, TPM module replacement, microcode updates and dbx policy are separate features. When requested alongside CA 2023, track each feature's changes and validation independently.
