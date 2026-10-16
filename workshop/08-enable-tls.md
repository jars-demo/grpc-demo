# 08 · Enable TLS

> ⏱ 15 minutes · Secure the gRPC connection, then prove the bytes are no longer readable.

## Learning objectives

- Configure TLS on a gRPC server (certificate + private key) and a client (trusted CA).
- Show, on the wire, what TLS hides and what it does not.
- Read how this repository configures listeners and fails fast on bad configuration.

## Prerequisites

Chapters 02, 03 and 05. The stack is running.

## Concept

Server side (`services/common/tls.py`, `services/grpc_server/server.py`):

```python
creds = grpc.ssl_server_credentials([(private_key_pem, certificate_chain_pem)])
server.add_secure_port("0.0.0.0:50051", creds)
```

Client side (`services/common/tls.py`):

```python
creds = grpc.ssl_channel_credentials(root_certificates=ca_pem)
channel = grpc.secure_channel("localhost:50051", creds)
```

That is all TLS needs: the server proves its identity with a key and certificate; the client says which CA it trusts. gRPC then **always** verifies the chain and the hostname - the Python API for secure channels has no switch to skip it, and this repository adds none.

One server process can listen several ways at once. The Docker `grpc-server` runs two listeners with the same servicers:

| Listener | Variable | Default | Credentials |
| --- | --- | --- | --- |
| TLS | `GRPC_TLS_PORT` | 50051 | server certificate |
| mutual TLS | `GRPC_MTLS_PORT` | 50052 | server certificate + required client certificate (chapter 10) |
| plaintext | `GRPC_PLAINTEXT_PORT` | 0 (off) | none; loopback only |

All settings are read and validated in one place, `services/common/config.py`, and documented in `.env.example`.

## Exercise

### 1. A TLS call, with the connection settings shown

```bash
uv run python -m grpc_client --show-connection hello --name Ada
```

**Expected:**

```text
# tls -> localhost:50051  ca=certs/out/ca.crt  cert=-  deadline=5.0s
Hello, Ada!
  transport security: tls
  served at:          13:13:43.858 UTC
  status:             OK
```

(On Windows the path prints as `certs\out\ca.crt`.)

### 2. Put the tap in front of TLS

Terminal 2:

```bash
uv run python examples/wire_tap.py --listen 50061 --forward localhost:50051
```

Terminal 1:

```bash
uv run python -m grpc_client --target localhost:50061 hello --name Ada
```

**Expected** in the tap (bytes differ every time - that is the point):

```text
[conn 1] client -> server 1463 bytes | …….}…c.6.Sa.%……...Da..= )...&]W.S……{..D.."._G……..+.,./.0...W…....localhost………………..#…....h2…………....3t...
[conn 1] server -> client 2005 bytes | ……..!..N...(..f..N....=1..u.A..e..} )...&]W.S……{..D.."._G…..n.3.d...`…*P..
```

Compare with chapter 03: no `:path`, no `Ada`, no `Hello, Ada!`, no frame list - the tap cannot even find HTTP/2 frames. Two words remain readable in the first packet, the ClientHello: **`localhost`** (the SNI - which server the client wants) and **`h2`** (ALPN). Metadata like that, plus IP addresses, ports, timing and sizes, stays visible under TLS.

Why did this work through a relay on a different port? The client verified the certificate against the *name* in its target, `localhost`, which is in the SAN. TLS authenticates names, not ports or paths.

### 3. Search the capture

Stop the tap (Ctrl+C) and run it again, this time saving what it sees to a file (`>` works the same in PowerShell and bash):

```bash
uv run python examples/wire_tap.py --listen 50061 --forward localhost:50051 > tap-tls.log
```

Repeat the client call from step 2, stop the tap, and search the capture for the name you sent:

```powershell
Select-String -Pattern Ada -Path tap-tls.log
```

```bash
grep Ada tap-tls.log
```

**Expected:** no match. Do the same with the chapter 03 plaintext setup and the search finds `Ada` in the `DATA` frame. Delete `tap-tls.log` afterwards.

## What just happened

The same HTTP/2 frames travelled inside TLS records. An observer still sees that *some* client talked to `localhost:50061`, when, and roughly how much - but not which method, which arguments, or which answer. And because the client verified the server certificate, a relay that tried to present its own certificate instead of passing the bytes through would have been rejected.

## Common failure: the server cannot find its certificate

Start a server with a typo in the certificate path (on a spare port, so it does not clash with Docker).

bash/zsh:

```bash
GRPC_TLS_PORT=50071 GRPC_MTLS_PORT=0 GRPC_SERVER_CERT_FILE=nope.crt uv run python -m grpc_server
```

PowerShell:

```powershell
$env:GRPC_TLS_PORT="50071"; $env:GRPC_MTLS_PORT="0"; $env:GRPC_SERVER_CERT_FILE="nope.crt"
uv run python -m grpc_server
Remove-Item Env:GRPC_TLS_PORT, Env:GRPC_MTLS_PORT, Env:GRPC_SERVER_CERT_FILE
```

**Expected:**

```text
error: server certificate not found: nope.crt
Generate the workshop certificates with: uv run python certs/scripts/certs.py generate
```

The server refuses to start rather than starting without TLS. Configuration problems surface at startup, with the variable or file named. Similarly, asking for plaintext on a public address:

```bash
GRPC_BIND_HOST=0.0.0.0 GRPC_PLAINTEXT_PORT=50050 uv run python -m grpc_server
```

```text
error: Invalid configuration:
  GrpcServerSettings: Value error, plaintext gRPC is only allowed on a loopback address, not '0.0.0.0'; use the TLS listener for anything reachable from another machine or container
```

## Knowledge check

1. What two things does a gRPC TLS server need? What one thing does the client need?
2. Name three things an observer can still learn about a TLS-protected gRPC call.
3. Why does the server exit instead of falling back to plaintext when the certificate is missing?

<details>
<summary>Answers</summary>

1. Server: private key and certificate (chain). Client: the CA certificate(s) it trusts.
2. Any three of: client and server IP addresses and ports, the server name (SNI), the ALPN protocol, timing, message sizes, connection count.
3. A silent fallback would turn a configuration mistake into an undetected security failure. Failing loudly gets it fixed.

</details>

## Done when

The tap shows ciphertext for a TLS call, and you can point to the two readable words in the ClientHello.

Next: [09 · Certificate Validation](09-certificate-validation.md)
