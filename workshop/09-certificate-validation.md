# 09 · Certificate Validation

> ⏱ 20 minutes · Break each verification check on purpose, read the error, then issue and rotate certificates.

## Learning objectives

- Trigger, recognize and explain the three most common verification failures: untrusted issuer, hostname mismatch, expired certificate.
- Inspect a certificate's issuer, SAN and validity with OpenSSL.
- Issue and rotate a server certificate without touching any client.

## Prerequisites

Chapters 02 and 08. The stack is running (it includes `grpc-expired` on port 50053).

## Concept

A TLS client accepts a server certificate only if **all** of these hold:

| Check | Question | Failure in gRPC (`details`) |
| --- | --- | --- |
| Chain | Does the certificate chain up to a CA I trust? | `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` |
| Hostname | Is the name or IP I connected to in the SAN? | `Hostname Verification Check failed` |
| Validity | Is *now* between notBefore and notAfter? | `CERTIFICATE_VERIFY_FAILED: certificate has expired` |
| Possession | Did the server sign the handshake with the matching private key? | handshake failure |

Each check stops a different attack: an impostor's self-made certificate (chain), a valid certificate for a *different* site (hostname), a stolen key from a long-retired certificate (validity), a copied public certificate without its key (possession).

Every failure below happens in the **TLS handshake**, before any RPC is sent, so gRPC reports them as `UNAVAILABLE`: no usable connection. You will also see gRPC's own log line (`I1016 ... Handshake failed with error ...`) on stderr; it carries the same reason.

## Exercise

### 1. Untrusted issuer

Trust gRPC's bundled public CAs instead of the workshop CA:

```bash
uv run python -m grpc_client --system-roots hello
```

**Expected:**

```text
RPC failed: UNAVAILABLE
  details: failed to connect to all addresses; last error: UNKNOWN: ipv4:127.0.0.1:50051: Tls handshake failed (TSI_PROTOCOL_FAILURE): SSL_ERROR_SSL: error:1000007d:SSL routines:OPENSSL_internal:CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate: OK
  meaning: No usable connection: the server is down, the port is wrong, or the TLS handshake failed. (REST: connection error / 503)
  hint:    The client could not build a chain from the server certificate to a CA it trusts. --ca must be the CA that issued the server certificate (compare issuer and subject with certs.py inspect).
```

`--ca certs/out/rogue-ca.crt` fails identically. Compare the issuer of the server certificate with the subject of each CA:

```bash
uv run python certs/scripts/certs.py inspect server
uv run python certs/scripts/certs.py inspect rogue-ca
```

### 2. Hostname mismatch

The server certificate lists `DNS:localhost, DNS:grpc-server, DNS:rest-https` and **no IP addresses**. Connect by IP:

```bash
uv run python -m grpc_client --target 127.0.0.1:50051 hello
uv run python examples/tls_inspect.py 127.0.0.1 50051
```

**Expected:**

```text
RPC failed: UNAVAILABLE
  details: failed to connect to all addresses; last error: UNKNOWN: ipv4:127.0.0.1:50051: Custom verification check failed with error: UNAUTHENTICATED: Hostname Verification Check failed.
```

```text
certificate verification failed: IP address mismatch, certificate is not valid for '127.0.0.1'. (code 64)
```

Same machine, same port, same certificate - only the *name* changed. The chain check passed; the hostname check did not.

### 3. Expired certificate

```bash
uv run python certs/scripts/certs.py inspect expired-server
uv run python -m grpc_client --target localhost:50053 hello
```

**Expected:** `notBefore=Jan  1 00:00:00 2024 GMT` and `notAfter=Jan 31 00:00:00 2024 GMT`, then:

```text
RPC failed: UNAVAILABLE
  details: ... CERTIFICATE_VERIFY_FAILED: certificate has expired: OK
  hint:    The server certificate is outside its validity period. The fix is a new certificate on the server (certs.py rotate), never a client that ignores expiry.
```

The issuer is the trusted workshop CA and the SAN includes `localhost`. Only the dates are wrong, and that is enough.

### 4. Verify every certificate at once

```bash
uv run python certs/scripts/certs.py verify
```

**Expected:**

```text
Verifying against certs/out/ca.crt (the workshop CA):

  server.crt           OK                                                   [as expected]
  expired-server.crt   FAIL: certificate has expired                        [as expected]
  client.crt           OK                                                   [as expected]
  admin.crt            OK                                                   [as expected]
  rogue-client.crt     FAIL: unable to get local issuer certificate         [as expected]

  server.key matches server.crt: yes
```

This runs `openssl verify -CAfile certs/out/ca.crt -purpose sslserver|sslclient <cert>` for each certificate - the same chain, validity and key-usage checks, offline.

### 5. Issue and rotate the server certificate

Certificates are short-lived on purpose (90 days here; public CAs are moving to even shorter lifetimes). Rotation issues a **new key and certificate from the same CA**. Clients trust the CA, not the individual certificate, so they need no change.

```bash
uv run python examples/tls_inspect.py localhost 50051
uv run python certs/scripts/certs.py rotate server
docker compose restart grpc-server rest-https
uv run python examples/tls_inspect.py localhost 50051
uv run python -m grpc_client hello
```

**Expected:** the `serial:` line differs between the first and second `tls_inspect`, `certs.py` prints `Rotated server: serial <old> -> <new>`, and `hello` still succeeds. Read `rotate()` and `issue_leaf()` in `certs/scripts/certs.py` to see the `openssl req` and `openssl ca` commands it runs - they are also printed as it runs.

A server reads its certificate at startup, which is why it needs the restart. (If a container still serves the old serial, recreate it: `docker compose up -d --force-recreate grpc-server rest-https`.)

## What just happened

Each failure corresponded to exactly one check, and each error message named it - if you read the `details` past `failed to connect to all addresses`. In every case the correct fix was on the **certificate side** (trust the right CA, connect with a name in the SAN, issue a new certificate), never on the verification side.

## Common failure: "fixing" a hostname mismatch by overriding the name

gRPC has a channel option, `grpc.ssl_target_name_override`, that makes the client check a different name than the one it connected to. It exists for testing and it hides exactly the mismatch you just diagnosed. This repository's hygiene test rejects it in the code. The real fixes are: connect with a name the certificate lists, or reissue the certificate with the name you need in its SAN.

## Knowledge check

1. Why does connecting to `127.0.0.1` fail while `localhost` works, if both reach the same server?
2. A certificate expired yesterday. Who must act, client or server operator?
3. After rotating `server.crt`, why do clients not need a new `ca.crt`?

<details>
<summary>Answers</summary>

1. Verification compares the *connection name* with the SAN. `localhost` is listed; the IP address is not.
2. The server operator: issue and deploy a new certificate. A client that ignores expiry is a vulnerability.
3. They trust the issuing CA; the new certificate is signed by the same CA.

</details>

## Done when

You have produced all three failures, read the reason in each, and rotated the server certificate with clients still connecting.

Next: [10 · Mutual TLS](10-mutual-tls.md)
