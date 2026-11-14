UEFI CA 2023 Auto Detect 1.0.0 — Portable Windows x64

Extract this entire ZIP into a folder, then run UEFI-CA2023-AutoDetect.exe.
Keep the _internal folder beside the executable. Windows 10/11 x64 is required.
No Python installation, pip, OpenSSL installation, administrator access or
Internet connection is needed to run the patcher. This is a portable EXE with
its dependency folder, rather than an installer or a lone EXE file.

1. Open an extracted stock .bin/.rom image.
2. Click Analyse to inspect the detected layout and native enrollment family.
3. For an eligible image, create your encrypted owner key pair in a private
   local folder, or load an existing encrypted PEM and matching public DER.
   Keep the private key and password safe. No private key is supplied here.
4. Confirm the checkbox selecting replacement of the AMI test PK by your owner
   certificate. Click Analyse again and enter your private-key password.
5. Read the live log. Save As becomes available only after all checks pass.
6. Save under a new name. The patcher writes the image, .report.json and
   .log.txt sidecars and verifies their bytes. It refuses existing files and
   protects the original input.

The supplied native-driver family recognition, original factory key baseline,
FIT/FFS/space checks, certificate pins, owner/key matching, Auth2 signatures,
unchanged-byte checks and mandatory independent UEFIExtract validation remain
enforced. Unknown native code or unsupported layouts stay inspection-only.
No force-patch option is provided. A new implementation needs review once;
compatible images do not need a separate whole-BIOS profile.

The patch replaces the factory AMI test PK with your public owner certificate,
adds the Microsoft 2023 KEK and three 2023 db certificates, retains the original
2011 KEK/db entries and leaves dbx unchanged. Newly generated firmware needs
its own hardware/enrollment/Windows verification. The application does not
flash hardware or change this PC's enrolled Secure Boot keys.

Included: Python/Tk runtime, cryptography, native OpenSSL, UEFIExtract, the four
original Microsoft DER certificates, reviewed family metadata and license
notices under _internal/licenses. The ZIP contains no motherboard firmware,
private signing keys, passwords or personal reports. Dependencies are checked
against the included manifest at startup. No Authenticode publisher signature
is applied to this build; verify the published ZIP hash before running it.

Source and complete documentation:
https://github.com/BegemotX99/uefi-ca2023-agent-kit

Developer smoke test (no firmware needed):
UEFI-CA2023-AutoDetect.exe --self-test C:\path\package-test.json
The result is written as JSON. Tests generate only ephemeral temporary keys.
