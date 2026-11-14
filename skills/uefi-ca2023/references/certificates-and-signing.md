# Certificate content, ownership and Auth2 signatures

## Certificate identity

| Variable | Certificate | SHA-256 over DER certificate bytes |
|---|---|---|
| KEK | Microsoft Corporation KEK 2K CA 2023 | `3cd3f0309edae228767a976dd40d9f4affc4fbd5218f2e8cc3c9dd97e8ac6f9d` |
| db | Windows UEFI CA 2023 | `076f1fea90ac29155ebf77c17682f75f1fdd1be196da302dc8461e350a9ae330` |
| db | Microsoft UEFI CA 2023 | `f6124e34125bee3fe6d79a574eaa7b91c0e7bd9d929c1a321178efd611dad901` |
| db | Microsoft Option ROM UEFI CA 2023 | `e5be3e64c6e66a281457ecdece0d6d0787577aad2a3a0144262c10c14ba8d8f1` |

Obtain DER files from the KEK and DB certificate directories in Microsoft's repository. Pin the upstream revision and verify the downloaded bytes. The helper accepts arbitrary filenames ending in `.der` and requires these exact fingerprints. Confirm the applicable current issuer guidance before substituting another certificate generation. [Microsoft public objects](https://github.com/microsoft/secureboot_objects/tree/main/PreSignedObjects) · [Microsoft creation and management guidance](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-secure-boot-key-creation-and-management-guidance?view=windows-11)

The Windows CA authorizes the newer Windows boot chain. The Microsoft KEK authorizes database servicing. Third-party UEFI and Option ROM CAs extend the corresponding trust policy. The original migration preserved the existing 2011 compatibility entries. dbx revocations are a separate policy and servicing task.

## Owner policy

| Desired outcome | Required engineering decision |
|---|---|
| Preserve an enrolled OEM PK | Obtain an update authorized by that PK, or use the firmware's documented physically present management flow where supported. |
| Preserve OEM factory PK while updating defaults | Review the factory enrollment sequence and accepted packaging. This needs a dedicated adapter and test. |
| Replace an AMI test PK with a locally controlled owner PK | Generate an encrypted local RSA key pair and explicitly select owner-PK migration. The supplied builder implements this path on reviewed inputs. |
| Share a maintainer-managed firmware line | Publish the public certificate and key-control policy. Keep private signing capability under maintainer custody and obtain the user's choice to enroll it. |

Public DER certificates, fingerprints and signed release manifests can be published. An encrypted private key still belongs in a private custody system. Once private key material is public, password strength alone is insufficient grounds to keep using that identity. Rotation and re-enrollment are required if confidentiality has been lost.

The tool's `keygen` command creates a fresh RSA-3072 key, an encrypted PKCS#8 PEM file and a self-signed 10-year public DER certificate. It requires matching passwords of at least 12 bytes. Choose a distinct key per independent owner and retain the password securely. Certificate and key paths must be unused. Public certificates from past project builds identify their original maintainer, and do not provide another user's local signing identity.

PK is the platform policy authority. It can authorize KEK changes. Keys in KEK normally authorize db/dbx changes. Adding a self-signed owner PK does not make that owner certificate a Microsoft signing certificate. Microsoft private keys are unnecessary for adding Microsoft's public certificates to factory defaults under a permitted owner policy. [UEFI Secure Boot architecture](https://uefi.org/specs/UEFI/2.11/32_Secure_Boot_and_Driver_Signing.html)

## EFI_SIGNATURE_LIST

For one X.509 entry with an empty signature header, serialize the following structure. Integers are little-endian and GUIDs use UEFI byte order.

| Offset | Field | Value |
|---|---|---|
| 0x00 | SignatureType | X.509 GUID `A5C059A1-94E4-4AA7-87B5-AB155C2BF072` |
| 0x10 | SignatureListSize, UINT32 | `44 + DER byte count` |
| 0x14 | SignatureHeaderSize, UINT32 | 0 |
| 0x18 | SignatureSize, UINT32 | `16 + DER byte count` |
| 0x1C | SignatureOwner | 16-byte owner GUID |
| 0x2C | SignatureData | Full DER certificate |

Append complete lists to an existing payload when preserving its old lists. Validate all entry lengths, list boundaries and DER fingerprints. Hash the certificate itself for identity. Hashing the wrapper, ESL or complete variable produces a different value.

## Auth2

The reviewed AMI default files use a time-based authenticated variable representation. Its serialized object contains `EFI_TIME`, then `WIN_CERTIFICATE_UEFI_GUID`, then PKCS#7 data, then the ESL payload. The certificate-type GUID is `4AAFD29D-68DF-49EE-8AA9-347D375665A7`. Validate wrapper length, revision `0x0200` and type `0x0EF1`.

The signed bytes comprise the variable name encoded UTF-16LE without the trailing NUL, the vendor GUID, UINT32 attributes, EFI_TIME and the complete new payload. The reviewed enrollment path uses attributes `0x27`. An arbitrary live update can use other attributes, so establish them from its target interface. Setup Mode changes authentication requirements, while the variable representation still needs correct formatting. [UEFI variable services](https://uefi.org/specs/UEFI/2.10/08_Services_Runtime_Services.html)

The helper generates detached RSA/SHA-256 CMS signatures and verifies them independently with OpenSSL. Its `-noverify` option skips external certificate chain policy during this local signature check. The signing identity is separately checked by matching the local owner key to the intended certificate. The helper extracts the bare SignedData required by the reviewed legacy AMI path before assembling the Auth2 object. Test exact DER packaging against the native reader. A valid modern CMS ContentInfo container can still be incompatible with an older reader.

After modifying any signed payload, rebuild and verify the signature. A fresh timestamp and local signature can change the output hash on every build. The factory object is installed through the board's factory enrollment sequence. A direct User Mode update must meet the enrolled keys' authorization and replay requirements as well.
