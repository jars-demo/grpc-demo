# Command reference

All commands run from the repository root. They work the same in PowerShell, bash and zsh unless noted. `make <task>` is equivalent to `python scripts/tasks.py <task>` if you have make.

## Task runner (`scripts/tasks.py`)

| Task | Does | Needs |
| --- | --- | --- |
| `setup` | `uv sync`, `npm ci` in `frontend/`, generate certificates | uv, (Node 22), OpenSSL |
| `certs` | generate certificates if missing | uv, OpenSSL |
| `generate-proto` | regenerate `services/generated/` from `services/proto/` | uv |
| `lint` | `ruff check`, `ruff format --check`, generated-code consistency | uv |
| `format` | `ruff format`, `ruff check --fix` | uv |
| `typecheck` | `mypy` (strict) | uv |
| `test` | unit, gRPC, TLS/mTLS, certificate, challenge and hygiene tests (no Docker) | uv, OpenSSL |
| `test-integration` | the smoke checks as pytest tests against the running stack | uv, running stack |
| `frontend-check` | lint, typecheck, format check, tests, static build of the website | Node 22 |
| `check` | `lint` + `typecheck` + `test` (+ `frontend-check` if installed) | as above |
| `up` | `docker compose up --build --detach --wait` (checks certificates first) | Docker |
| `down` | `docker compose down` | Docker |
| `logs [service]` | follow container logs | Docker |
| `smoke-test` | 21 end-to-end checks against the running stack | uv, running stack |
| `clean` | remove caches, build output, challenge working copies (keeps certificates) | - |

Run as `uv run python scripts/tasks.py <task>` (or plain `python scripts/tasks.py <task>`; the runner itself uses only the standard library).

## Certificate lab (`certs/scripts/certs.py`)

```bash
uv run python certs/scripts/certs.py generate [--force]
uv run python certs/scripts/certs.py list
uv run python certs/scripts/certs.py inspect {ca,rogue-ca,server,expired-server,client,admin,rogue-client}
uv run python certs/scripts/certs.py verify
uv run python certs/scripts/certs.py rotate {server,expired-server,client,admin,rogue-client}
uv run python certs/scripts/certs.py regenerate
uv run python certs/scripts/certs.py clean
```

`--out DIR` (before the subcommand) writes somewhere other than `certs/out/`.

## gRPC server and client

```bash
uv run python -m grpc_server                    # TLS :50051 + mTLS :50052 (needs ports free)
uv run python -m grpc_server --plaintext        # + plaintext localhost:50050
uv run python -m grpc_server --plaintext-only   # only plaintext localhost:50050

uv run python -m grpc_client [connection options] <command>
```

Connection options: `--target host:port` · `--ca FILE` or `--system-roots` · `--cert FILE --key FILE` (mTLS) · `--plaintext` (loopback only) · `--deadline SECONDS` · `--profile FILE.toml` · `--show-connection`.

| Command | RPC | Example |
| --- | --- | --- |
| `hello [--name N] [--language L] [--delay-ms MS]` | `SayHello` | `hello --name Ada --language hi` |
| `topics [--layer L]` | `ListTopics` | `topics --layer security` |
| `topic ID` | `GetTopic` | `topic grpc` |
| `watch [--count N] [--interval-ms MS]` | `WatchEvents` (server streaming) | `watch --count 4 --interval-ms 500` |
| `record [VALUES...] [--label L] [--measure-hello N]` | `RecordMeasurements` (client streaming) | `record --measure-hello 20` |
| `chat [MESSAGES...] [--pause-ms MS]` | `Chat` (bidirectional; stdin if no messages) | `chat "hi" "there" --pause-ms 300` |
| `stats` | `AdminService.GetServerStats` (mTLS + authz) | with `--cert certs/out/admin.crt --key certs/out/admin.key` |
| `health` | `grpc.health.v1.Health/Check` | `health` |

Exit codes: `0` success, `1` the RPC failed (explained on stderr), `2` invalid configuration.

## REST API

```bash
uv run python -m rest_api              # http://127.0.0.1:8080
uv run python -m rest_api --https      # https://127.0.0.1:8443 with certs/out/server.*
uv run python examples/rest_client.py URL [--name N --language L --delay-ms MS] [--post JSON] [--ca FILE] [--timeout S]
```

## Examples

| Command | Shows |
| --- | --- |
| `uv run python examples/wire_tap.py --listen PORT --forward HOST:PORT` | bytes on the wire; HTTP/2 frames when plaintext |
| `uv run python examples/tls_inspect.py HOST PORT [--ca FILE]` | TLS version, cipher, ALPN, certificate, serial |
| `uv run python examples/wire_format.py` | protobuf vs JSON bytes |
| `uv run python examples/plaintext_loopback.py` | a complete in-process plaintext round trip |
| `uv run python examples/multiplex.py [--plaintext --target ...]` | three streams on one connection |
| `uv run python examples/contract_mismatch.py` | `UNIMPLEMENTED` from a mismatched contract |
| `uv run python examples/latency_compare.py [--calls N] [--fresh-connections]` | REST vs gRPC latency, connection reuse |

## Final challenge

```bash
uv run python -m challenge start [--force]
uv run python -m challenge list
uv run python -m challenge run NN
uv run python -m challenge hint NN
uv run python -m challenge check NN|all
uv run python -m challenge reset NN
```

## Docker-only equivalents

```bash
docker compose --profile tools run --rm --no-deps toolbox python certs/scripts/certs.py generate
docker compose --profile tools run --rm toolbox python -m grpc_client --target grpc-server:50051 hello
docker compose --profile tools run --rm toolbox python -m grpc_client --target grpc-server:50052 --cert certs/out/client.crt --key certs/out/client.key hello
docker compose --profile tools run --rm toolbox curl -sS --cacert certs/out/ca.crt https://rest-https:8443/v1/topics
docker compose --profile tools run --rm toolbox openssl s_client -connect grpc-server:50051 -servername grpc-server -alpn h2 -CAfile certs/out/ca.crt
docker compose --profile tools run --rm toolbox python examples/plaintext_loopback.py
docker compose --profile tools run --rm challenge start
docker compose --profile tools run --rm challenge run 01
```

Inside the Compose network the services are `grpc-server`, `grpc-expired`, `rest-http`, `rest-https`.

## Website

```bash
cd frontend
npm ci
npm run dev            # http://localhost:3000, live reload
npm run lint
npm run typecheck
npm run format:check
npm test
npm run build          # static export into frontend/out
```
