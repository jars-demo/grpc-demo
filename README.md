# gRPC & HTTPS — From Requests to Secure RPC

*Understand how HTTP, TLS, HTTP/2, and gRPC work together. Build a real service, secure the connection, and learn to diagnose the failures that matter.*

[Website](https://grpc.jishanahmed.in) · [Workshop](workshop/00-overview.md) · [Architecture](docs/architecture.md) · [Security](docs/security.md) · [Troubleshooting](docs/troubleshooting.md) · [Commands](docs/commands.md)

A hands-on, self-paced workshop from [JARS DEMO](https://github.com/jars-demo). You run a small **Workshop Service** that speaks both **gRPC** and **REST**, generate your own **local certificate authority**, secure the connection with **TLS** and **mutual TLS**, and then break it on purpose - untrusted CAs, hostname mismatches, expired certificates, missing client certificates, authorization failures - to learn what each error means and how to fix it properly.

> **Don't just explain the protocol. Observe it, break it, and fix it.**

> Educational project. The services, certificates and keys exist to teach; do not deploy them as they are and never trust the workshop CA outside the workshop. See [docs/security.md](docs/security.md#before-production).

## What you will learn

HTTP → HTTPS → TLS → HTTP/2 → Protocol Buffers → gRPC → streaming → certificate validation → mutual TLS → troubleshooting, in [14 chapters](workshop/) (about 3¾ hours):

| # | Chapter | Min |
| --- | --- | --- |
| 00 | [Overview and Setup](workshop/00-overview.md) | 10 |
| 01 | [How HTTP Works](workshop/01-how-http-works.md) | 15 |
| 02 | [HTTPS and TLS](workshop/02-https-and-tls.md) | 20 |
| 03 | [HTTP/2 Fundamentals](workshop/03-http2-fundamentals.md) | 15 |
| 04 | [Protocol Buffers](workshop/04-protocol-buffers.md) | 15 |
| 05 | [Your First gRPC Call](workshop/05-first-grpc-call.md) | 15 |
| 06 | [REST vs gRPC](workshop/06-rest-vs-grpc.md) | 10 |
| 07 | [Streaming RPCs](workshop/07-grpc-streaming.md) | 20 |
| 08 | [Enable TLS](workshop/08-enable-tls.md) | 15 |
| 09 | [Certificate Validation](workshop/09-certificate-validation.md) | 20 |
| 10 | [Mutual TLS](workshop/10-mutual-tls.md) | 15 |
| 11 | [Debugging Clinic](workshop/11-debugging-clinic.md) | 15 |
| 12 | [Performance and Deadlines](workshop/12-performance-and-deadlines.md) | 15 |
| 13 | [Final Challenge](workshop/13-final-challenge.md) | 25 |

Along the way you read raw HTTP/1.1 and decoded HTTP/2 frames through a wire tap, see what TLS hides (and what it doesn't: the SNI), decode protobuf bytes by hand, stream in all four gRPC patterns, rotate a certificate without touching clients, and measure latency honestly.

## Prerequisites

| Tool | Version | For |
| --- | --- | --- |
| [Docker Desktop](https://docs.docker.com/get-docker/) (Windows, macOS) or Docker Engine + Compose v2 (Linux) | Compose 2.20+ | the services and the website |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | 0.5+ | Python 3.13 (installed for you), clients, examples, tests |
| OpenSSL | 1.1.1 or 3.x | certificates. Windows: ships with [Git for Windows](https://gitforwindows.org/). No OpenSSL? Use the Docker command below. |
| Node.js | 22 | only to build or develop the website |

No cloud account, API key or paid service is needed. Every command below works in **PowerShell** and in **bash/zsh**, from the repository root.

## Start the environment

```bash
git clone https://github.com/jars-demo/grpc-demo.git
cd grpc-demo
uv sync
uv run python certs/scripts/certs.py generate
uv run python scripts/tasks.py up
uv run python scripts/smoke_test.py
```

The smoke test makes 21 real checks and ends with `21/21 checks passed`. The stack is:

| Service | Address (loopback only) | What |
| --- | --- | --- |
| `grpc-server` | `localhost:50051` TLS, `localhost:50052` mutual TLS | gRPC Workshop Service + AdminService |
| `grpc-expired` | `localhost:50053` | a server with an expired certificate (fails on purpose) |
| `rest-http` / `rest-https` | `http://localhost:8080`, `https://localhost:8443` | the REST API |
| `web` | <http://localhost:3000> | this workshop's website |

Without OpenSSL, generate the certificates in the toolbox container instead: `docker compose --profile tools run --rm --no-deps toolbox python certs/scripts/certs.py generate`. If you have `make`, `make up`, `make test` and so on wrap the same `scripts/tasks.py` tasks.

## Your first requests

REST over HTTPS, verified against the workshop CA:

```bash
uv run python examples/rest_client.py https://localhost:8443/v1/greetings --name Ada
```

gRPC over TLS (the client's default):

```bash
uv run python -m grpc_client hello --name Ada
```

```text
Hello, Ada!
  transport security: tls
  served at:          13:13:43.858 UTC
  status:             OK
```

The introductory plaintext exercise (loopback only, [chapter 05](workshop/05-first-grpc-call.md)) runs a local server: `uv run python -m grpc_server --plaintext-only`, then `uv run python -m grpc_client --plaintext --target localhost:50050 hello`.

## TLS and mutual TLS

TLS is on by default: the client verifies the server's certificate chain, hostname (SAN) and validity against `certs/out/ca.crt`. There is no option to skip verification. For mutual TLS, present a client certificate on port 50052:

```bash
uv run python -m grpc_client --target localhost:50052 --cert certs/out/client.crt --key certs/out/client.key hello
uv run python -m grpc_client --target localhost:50052 --cert certs/out/admin.crt --key certs/out/admin.key stats
```

The first succeeds with `client identity: workshop-client`; calling `stats` with that same trusted certificate returns `PERMISSION_DENIED`, because authentication is not authorization - only `workshop-admin` may read server stats. Chapters [08](workshop/08-enable-tls.md), [09](workshop/09-certificate-validation.md) and [10](workshop/10-mutual-tls.md) cover TLS, every validation failure, and mTLS.

## Where to begin

Open [workshop/00-overview.md](workshop/00-overview.md), or read the same chapters with progress tracking on the website: <http://localhost:3000> locally, or <https://grpc.jishanahmed.in>.

## Repository layout

```text
services/proto/       the .proto contract           services/generated/  generated bindings (do not edit)
services/core/        shared domain logic            services/common/     config, TLS, logging
services/grpc_server/ gRPC server                    services/grpc_client/ CLI client
services/rest_api/    FastAPI REST API               certs/               certificate lab (output: certs/out/, ignored)
challenge/            final challenge                examples/            wire tap, TLS inspector, latency, ...
workshop/             the chapters                   docs/                architecture, security, troubleshooting, ...
frontend/             website (Next.js, static)      scripts/             tasks, proto generation, smoke test
tests/                unit, security, integration
```

## Development

```bash
uv run python scripts/tasks.py check            # ruff, proto consistency, mypy --strict, pytest, website checks
uv run python scripts/tasks.py test-integration # against the running stack
uv run python scripts/tasks.py down
```

All tasks: [docs/commands.md](docs/commands.md). Validation results from the last full run: [docs/validation-report.md](docs/validation-report.md).

## Contributing

Contributions are welcome - especially clearer explanations and new *real* failure scenarios. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md), and [open an issue](https://github.com/jars-demo/grpc-demo/issues) for anything that did not work as documented.

## License and credits

MIT - see [LICENSE](LICENSE). Third-party components: [docs/third-party-notices.md](docs/third-party-notices.md).

Created and maintained by **[Jishanahmed AR Shaikh (JARS)](https://jishanahmed.in)** as part of **[JARS DEMO](https://github.com/jars-demo)**, independent open-source workshops and engineering labs.
