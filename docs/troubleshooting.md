# Troubleshooting

Start with the method from [chapter 11](../workshop/11-debugging-clinic.md): status code → layer, details → cause, the other side's log when the client's view is thin.

## Setup and environment

| Symptom | Cause | Fix |
| --- | --- | --- |
| `openssl was not found on PATH` | OpenSSL missing | Windows: Git for Windows includes it (`C:\Program Files\Git\usr\bin`); add to PATH, or `docker compose --profile tools run --rm --no-deps toolbox python certs/scripts/certs.py generate`. macOS: `brew install openssl`. Linux: install the `openssl` package. |
| `error: certificates missing (...)` from `tasks.py up` | `certs/out/` empty | `uv run python certs/scripts/certs.py generate` |
| `Bind for 127.0.0.1:8080 failed: port is already allocated` | another process uses the port | stop it, or copy `.env.example` to `.env` and set e.g. `REST_HTTP_HOST_PORT=18080` (then use that port in commands) |
| `grpc-server` stays `unhealthy` on Linux | containers cannot read the `0600` keys | start with `python scripts/tasks.py up`, which sets `LOCAL_UID`/`LOCAL_GID`; or export them yourself: `LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up -d --wait` |
| `invalid mount config ... bind source path does not exist` | a certificate file is missing | generate certificates; the mounts deliberately refuse to create empty paths |
| `ModuleNotFoundError: No module named 'grpc_client'` | not run through uv, or not from the repo root | run `uv sync`, then `uv run python -m ...` from the repository root |
| `RuntimeError: The grpc package installed is at version ...` | generated code newer than `grpcio` | `uv sync` (versions are pinned together) |
| Greeting prints `?????` on Windows | legacy console code page | use Windows Terminal; the clients already write UTF-8 |

## gRPC call failures

| Status | Details contain | Meaning | Next step |
| --- | --- | --- | --- |
| UNAVAILABLE | `errors resolving` | DNS: name unknown here | from your machine use `localhost`; Compose names work only inside Compose |
| UNAVAILABLE | `Connection refused` | nothing listening | `docker compose ps`; check the port |
| UNAVAILABLE | `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` | wrong trust anchor | use `--ca certs/out/ca.crt`; `certs.py inspect server` |
| UNAVAILABLE | `Hostname Verification Check failed` | name not in SAN | connect via `localhost`; `certs.py inspect server` |
| UNAVAILABLE | `certificate has expired` | server cert out of date | `certs.py rotate server` + restart (the `grpc-expired` service is meant to fail) |
| UNAVAILABLE | `End of TCP stream` or `Connection aborted` | server rejected the handshake | `docker compose logs grpc-server --since 5m`; `PEER_DID_NOT_RETURN_A_CERTIFICATE` = no client cert, `CERTIFICATE_VERIFY_FAILED` = untrusted client cert |
| UNAVAILABLE | `WRONG_VERSION_NUMBER` | TLS client, plaintext server | check port / `--plaintext` |
| UNIMPLEMENTED | `Method not found!` | contract mismatch | compare client and server `.proto` versions |
| UNAUTHENTICATED | `requires a client certificate` | AdminService without mTLS | use port 50052 with `--cert/--key` |
| PERMISSION_DENIED | `not authorized` | identity lacks permission | use `admin.crt`, or change `GRPC_ADMIN_IDENTITIES` deliberately |
| DEADLINE_EXCEEDED | `Deadline Exceeded` | deadline shorter than the work | measure; set `--deadline` with headroom |
| INVALID_ARGUMENT | the rule that failed | bad request content | fix the request; do not retry |
| RESOURCE_EXHAUSTED | `larger than max` | message over the size limit | smaller payloads or `GRPC_MAX_MESSAGE_BYTES` |

You will also see gRPC core log lines like `I1016 12:52:15 ... ssl_transport_security.cc:2530] Handshake failed with error ...`. They come from the gRPC library itself and carry the same TLS reason. Set `GRPC_VERBOSITY=ERROR` to hide them.

## REST / HTTPS failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| `IP address mismatch, certificate is not valid for '127.0.0.1'` | name not in SAN | use `https://localhost:8443` |
| `unable to get local issuer certificate` | wrong CA | `--ca certs/out/ca.crt` |
| Windows curl: `schannel: ... revocation status is unknown` / `CERT_TRUST_REVOCATION_STATUS_UNKNOWN` | Windows' TLS library wants revocation info that a local CA does not publish | add `--ssl-revoke-best-effort` (keeps chain and hostname checks) or use `examples/rest_client.py` |
| PowerShell: `curl` behaves oddly | `curl` is an alias for `Invoke-WebRequest` in Windows PowerShell 5.1 | type `curl.exe` |
| `422` with `extra_forbidden` | unknown JSON field | send only `name`, `language`, `simulated_delay_ms` |
| `413` | body over `REST_MAX_BODY_BYTES` | smaller body |

## Challenge

| Symptom | Fix |
| --- | --- |
| `No working copy yet` | `uv run python -m challenge start` |
| `FAIL ... must trust exactly the workshop CA` although the call works | the checker also validates the profile; set `ca = "certs/out/ca.crt"` |
| Scenario passes locally but not in Docker | run Docker commands with the `challenge` service, which shares `grpc-server`'s network so `localhost` matches |
| Want to start over | `uv run python -m challenge reset NN` or `start --force` |

## Website

| Symptom | Fix |
| --- | --- |
| Diagrams show as code blocks | JavaScript disabled, or Mermaid failed to load; the diagram source and the surrounding text remain readable |
| Progress lost | progress lives in your browser's local storage; private windows and clearing site data reset it |
| `npm ci` fails on Node 18/20 | use Node 22 (`frontend/package.json` `engines`) |
