# Public owner certificates

The DER files and `manifest.json` identify the project-owned PK certificates used in earlier Qiyida H9S and Machinist MR9S builds. Each certificate contains its public key. Public-key publication lets users verify a build's identity and signatures.

The matching private keys remain encrypted in the original maintainer's local workspace. Enrolling one of these public certificates as PK grants its private-key holder authority over Secure Boot policy through valid authenticated updates. Certificate publication alone provides no signing service or promise of future updates.

For your own board, generate a fresh owner pair with the toolkit's `keygen` command and retain the encrypted private PEM outside the checkout. You may publish your public DER certificate, SHA-256 fingerprint, subject, validity and release association. Keep the private key and password under your control. A key committed to a public repository has lost its confidentiality and needs replacement.

For a shared maintainer-owned firmware line, publish the public certificate and key policy, protect the private key offline or with a suitable signing service, and define key rotation, recovery, custody and successor access. Users should knowingly select that policy before enrolling the PK. Use different keys for independent owners or product lines when their update authority should differ.
