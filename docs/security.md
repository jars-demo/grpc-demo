# Security guide: TLS, certificates and the workshop CA

This workshop handles certificates and private keys on purpose. This guide explains what is generated, how it is protected, what the code guarantees, and what would have to change before anything like it ran in production.

> **Educational project.** The certificate authority, keys and services here exist to teach. Never trust the workshop CA outside this workshop, never reuse its keys, and do not deploy these services as they are.

## What is generated

`uv run python certs/scripts/certs.py generate` creates, in `certs/out/` (ignored by Git and Docker):

| File | Issuer | Purpose | Key usage |
| --- | --- | --- | --- |
| `ca.crt`, `ca.key` | self | **JARS Workshop Local CA**, labelled "Local educational CA - do not trust outside the workshop" | `CA:TRUE, pathlen:0`; `keyCertSign, cRLSign` |
| `rogue-ca.crt`, `rogue-ca.key` | self | a second CA nothing trusts, for failure exercises | as above |
| `server.crt/.key` | workshop CA | gRPC TLS/mTLS and REST HTTPS; SAN `DNS:localhost, DNS:grpc-server, DNS:rest-https` | `CA:FALSE`; `digitalSignature`; EKU `serverAuth` |
| `expired-server.crt/.key` | workshop CA | validity 2024-01-01 to 2024-01-31 | as server |
| `client.crt/.key` | workshop CA | mTLS identity `workshop-client` | `CA:FALSE`; EKU `clientAuth` only |
| `admin.crt/.key` | workshop CA | mTLS identity `workshop-admin` | as client |
| `rogue-client.crt/.key` | rogue CA | same CN as `client`, untrusted issuer | as client |

All keys are ECDSA P-256. Leaf certificates are valid for 90 days, the CA for 365. Extensions come only from `certs/openssl/ca.cnf` (`copy_extensions = none`): a certificate request cannot smuggle in `CA:TRUE` or extra names.

## How key material is protected

- **Never committed.** `.gitignore` excludes `certs/out/`, `*.key`, `*.csr`, `.env`. A test (`tests/security/test_repository_hygiene.py`) fails if any tracked text file contains a private key, or if these ignore rules disappear.
- **Never in an image.** `.dockerignore` excludes `certs/out`, `**/*.key`, `**/*.pem`. Images contain code only.
- **Least privilege at runtime.** Each container bind-mounts only the files it needs, read-only: `grpc-server` gets `ca.crt`, `server.crt`, `server.key`; `rest-http` gets nothing. Mounts use `create_host_path: false`, so a missing file is an error instead of an empty directory.
- **File permissions.** Keys are written with mode `0600` (owner only) on Linux and macOS. On Linux, `scripts/tasks.py` runs the containers as your UID/GID so they can read them; containers never run as root.
- **Never exposed.** No API response, log line or web page includes key material. The website is a static build of Markdown and has no access to `certs/out/`.

## What the code guarantees

- **No verification bypass.** Secure channels use `grpc.ssl_channel_credentials`, which always verifies chain and hostname. `common/tls.channel_credentials` takes only a CA, certificate and key - a test pins that signature. The REST client always passes a CA file to `httpx`. Tests make sure the code never contains `verify=False`, `CERT_NONE`, `check_hostname = False`, `_create_unverified_context`, `ssl_target_name_override` or curl's `-k`, and that the docs never instruct you to use them.
- **No insecure fallback.** A missing or unreadable certificate stops the server at startup (`CertificateFileError`); it never starts without TLS. A TLS client pointed at a plaintext port fails (`WRONG_VERSION_NUMBER`) - tested.
- **Plaintext is fenced in.** The plaintext listener is off by default and refused unless bound to a loopback address; the client refuses plaintext to non-loopback targets.
- **Authentication is not authorization.** `AdminService` checks the verified client identity against `GRPC_ADMIN_IDENTITIES` on every call: no certificate gives `UNAUTHENTICATED`, a trusted certificate with another identity gives `PERMISSION_DENIED`. Tests cover both.
- **Bounded inputs.** gRPC messages are limited to 64 KiB (`GRPC_MAX_MESSAGE_BYTES`); REST bodies to 16 KiB (`REST_MAX_BODY_BYTES`, also for chunked uploads); names, labels, counts and delays are validated with explicit ranges.
- **Containers.** Non-root user, read-only root filesystem, all capabilities dropped, `no-new-privileges`, ports published on loopback only.

## The four ideas to keep apart

| | Question answered | Mechanism here |
| --- | --- | --- |
| Encryption in transit | Can others read or modify the traffic? | TLS |
| Server authentication | Am I talking to the real server? | client verifies server certificate (chain, SAN, validity) |
| Client authentication | Who is calling? | mutual TLS: server verifies client certificate |
| Authorization | May this caller do this? | application code (`grpc_server/admin.py`) |

TLS (even mutual) answers the first three. Only your application answers the fourth.

## Issuance and rotation workflow

1. **Issue:** `certs.py generate` runs, per certificate: `openssl ecparam -genkey` (new key), `openssl req -new` (request with a subject), `openssl ca -extensions <section>` (sign with the CA, extensions from config).
2. **Inspect:** `certs.py inspect <name>`; `certs.py list` shows expiry dates.
3. **Verify:** `certs.py verify` checks every certificate against the CA and that `server.key` matches `server.crt`.
4. **Rotate:** `certs.py rotate server` issues a new key and certificate from the same CA. Restart the users of the certificate: `docker compose restart grpc-server rest-https`. Clients need no change because they trust the CA.
5. **Start over:** `certs.py regenerate` creates a new CA and everything else. Restart the whole stack afterwards.

## Before production

This workshop deliberately omits things a production deployment needs:

- **Protect the CA key.** Use an HSM, a cloud KMS, or a managed private CA; use an offline root and online intermediates. Never keep a CA key next to the services.
- **Encrypt private keys at rest** and load them from a secret manager, not from files on disk.
- **Automate issuance and renewal** (ACME, cert-manager, SPIFFE/SPIRE), with short lifetimes and alerts well before expiry.
- **Revocation.** Publish CRLs or OCSP, or rely on very short-lived certificates.
- **Identity format.** Authorize on a structured identity (for example a SPIFFE ID in a URI SAN), not a free-text Common Name.
- **Authorization model.** Per-method policies, deny by default, audit logging of decisions.
- **TLS policy.** Pin minimum versions and cipher suites to your organization's policy; scan with standard tools.
- **Operational limits.** Rate limiting, keepalive and connection limits, request authentication for end users (tokens) on top of service identity.
- **Supply chain.** Pin base images by digest, sign images, generate SBOMs, scan continuously.

## Reporting a security issue

This is an educational repository, but if you find a way the code or the documentation could lead learners into an insecure practice, please open an issue at <https://github.com/jars-demo/grpc-demo/issues>. Do not include private keys in issues - even workshop ones.
