# AGENTS.md

Guidance for AI coding agents and developers working in this repository. Humans: start with [README.md](README.md).

## What this is

**gRPC & HTTPS - From Requests to Secure RPC**, a JARS DEMO workshop. A small Workshop Service exposed as gRPC (all four call patterns, plus an mTLS-only `AdminService` with authorization) and as a REST API (FastAPI), a local OpenSSL certificate lab, a CLI client with explained errors, examples that make the wire visible, a six-scenario final challenge, 14 chapters, and a static Next.js site at <https://grpc.jishanahmed.in>. Educational: never present it as production-ready.

## Map

```text
services/proto/grpcdemo/v1/workshop.proto  the contract (single source of truth for the gRPC API)
services/generated/                        generated bindings - NEVER edit; scripts/generate_proto.py
services/core/                             transport-independent logic shared by gRPC and REST
services/common/config.py                  the ONLY place that reads environment variables
services/common/tls.py                     credential loading; no verification bypass, by design
services/grpc_server/                      server (listeners), servicer, admin (authz), stats, health check
services/grpc_client/                      CLI: connection.py (modes, profiles), calls.py, diagnose.py
services/rest_api/                         FastAPI app, body size limit, entry point
certs/scripts/certs.py, certs/openssl/     certificate lab (stdlib + openssl CLI); output certs/out/ (ignored)
challenge/                                 scenarios.py, scenarios/NN.toml (broken profiles), runner
examples/                                  wire_tap, tls_inspect, wire_format, multiplex, latency, ...
workshop/NN-*.md                           chapters 00-13; the site renders them (no copies elsewhere)
docs/                                      architecture (diagram markers!), security, troubleshooting, commands, ...
frontend/                                  Next.js static export; reads ../workshop, ../docs, ../challenge/scenarios
scripts/tasks.py                           cross-platform task runner (Makefile wraps it); smoke_test.py
tests/                                     unit/, security/ (real TLS handshakes), integration/ (running stack)
```

## Commands

```bash
uv sync
uv run python certs/scripts/certs.py generate
uv run python scripts/tasks.py check            # ruff, proto --check, mypy --strict, pytest (+ frontend)
uv run python scripts/tasks.py up               # docker compose up --build --wait
uv run python scripts/tasks.py smoke-test       # 21 end-to-end checks
uv run pytest -m integration tests/integration
cd frontend && npm ci && npm run lint && npm run typecheck && npm run format:check && npm test && npm run build
```

## Rules

- **Never disable or bypass certificate verification**, in code, tests, examples or docs (no `verify=False`, `CERT_NONE`, `ssl_target_name_override`, curl `-k`). `tests/security/test_repository_hygiene.py` enforces it. Failures are fixed at the certificate, trust store or hostname.
- **Plaintext gRPC stays loopback-only** and off by default; TLS is the default path.
- **Never commit or bake in key material.** `certs/out/`, `*.key`, `.env` are ignored by Git and Docker. Containers mount only the files they need, read-only.
- **Generated code is generated.** Change the `.proto`, run `scripts/generate_proto.py`, commit both. CI runs `--check`. Keep `grpcio` and `grpcio-tools` on the same version.
- **Configuration only in `services/common/config.py`**, validated, documented in `.env.example`.
- **The chapters are the source of truth for the site.** Each starts with `# NN · Title` and `> ⏱ N minutes · summary` and has the sections the frontend tests require (objectives, prerequisites, concept, exercise, what just happened, common failure, knowledge check, done when).
- **Never fabricate output.** Every "Expected" block must come from actually running the command; label machine-specific numbers as such. If you change behaviour, re-run the affected chapter commands.
- **Diagrams in `docs/architecture.md` carry `<!-- diagram: id -->` markers** that the landing page uses; keep them.
- **Failure scenarios must be real** (a real misconfiguration producing a real error), deterministic and safe.
- Keep modules small, typed (`mypy --strict`), and readable by learners; prefer clear over clever.
- Do not add infrastructure (databases, brokers, meshes) without a specific exercise that needs it.
- Do not depend on other JARS DEMO repositories at runtime.
