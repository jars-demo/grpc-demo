# Validation report

Commands actually executed during the initial implementation, and what they returned. Nothing here is estimated or written by hand; where output varies per machine (timings, serials), that is stated.

- **Date:** 2026-10-16
- **Machine:** Windows 11 Home (10.0.26200), Git Bash and PowerShell 5.1
- **Tools:** Docker 28.2.2 / Compose v2.37.1 (Docker Desktop), uv 0.11.3, Python 3.13.7 (via uv), Node.js 22.12.0 / npm 10.9.0, OpenSSL 3.2.4, GNU Make 4.4.1

## 1. Clean-room run (what a new developer gets)

The files a `git clone` would contain (148 files, 1.2 MB: no `.venv`, `node_modules`, `certs/out`, build output or keys) were copied to an empty directory, and the documented flow was run there from zero:

| Step | Command | Result |
| --- | --- | --- |
| Setup | `uv run python scripts/tasks.py setup` | exit 0 - `Installed 37 packages`, `added 669 packages`, `Done. 2 CAs and 5 certificates in certs/out` |
| All checks | `uv run python scripts/tasks.py check` | exit 0 - ruff `All checks passed!`, `OK: 3 generated files match 1 .proto file(s)`, mypy `Success: no issues found in 33 source files`, pytest `130 passed, 1 skipped, 21 deselected`, vitest `71 passed`, eslint/tsc/prettier clean, `next build` 25 static pages |
| Start | `uv run python scripts/tasks.py up` | exit 0 - 2 images built, 5 containers `Healthy` |
| Smoke | `uv run python scripts/smoke_test.py` | `21/21 checks passed` |
| Integration | `uv run python scripts/tasks.py test-integration` | `21 passed` (3 httpx `DeprecationWarning`s - fixed afterwards, see §4) |
| Challenge (Docker) | `docker compose --profile tools run --rm challenge start` then `... challenge check all` | all six shipped scenarios `FAIL` as intended, `0/6 passed`, exit 1 |

The skipped test is `test_private_keys_are_owner_only`, which checks POSIX file modes and is skipped on Windows by design (it runs in Linux CI).

## 2. Python

| Command | Result |
| --- | --- |
| `uv run ruff check .` / `uv run ruff format --check .` | clean |
| `uv run python scripts/generate_proto.py --check` | `OK: 3 generated files match 1 .proto file(s)` |
| `uv run mypy` (strict) | `Success: no issues found in 33 source files` |
| `uv run pytest` | `130 passed, 1 skipped, 21 deselected` |
| `uv run pytest -m integration tests/integration -W error::DeprecationWarning` (stack running) | `21 passed` |

The 130 tests cover domain logic, configuration validation, the REST API (validation, 404/422/413 including chunked bodies, headers), all four gRPC patterns (incremental delivery, deadlines mid-stream, cancellation, size limits), TLS (untrusted CA, rogue CA, hostname mismatch, expired certificate, no plaintext fallback), mTLS (success, missing and untrusted client certificates), authorization (`UNAUTHENTICATED`, `PERMISSION_DENIED`, admin allowed), certificate properties, reproducible regeneration and rotation, every challenge scenario (fails as shipped, passes with the intended fix, rejects insecure fixes), and repository hygiene (no verification bypass in code or docs, ignore rules, loopback-only ports).

## 3. Website

| Command | Result |
| --- | --- |
| `npm run lint`, `npm run typecheck`, `npm run format:check` | clean |
| `npm test` | `71 passed` - every chapter parses and has the required sections, all relative links resolve, total duration 2-4 h, five architecture diagrams present, link rewriting, progress storage, filter/empty states, reset confirmation |
| `npm run build` | 25 static pages |
| `npm audit --omit=dev` | `found 0 vulnerabilities` (after upgrading mermaid 12.1.0 → 12.2.0 for a low-severity KaTeX advisory) |

Checked in Chrome (static build; the CSP and diagram checks also on the Docker `web` container): landing page, chapter reader (active chapter, table of contents, previous/next), progress persisting across pages and reloads, reset, light/dark/system theme, collapsed solutions, all five Mermaid diagrams rendering under the nginx Content-Security-Policy, no console errors, and no horizontal overflow at 390 px on the home, workshop, chapter and docs pages.

## 4. Running stack and exercises

Run against the Docker stack on this machine; every "Expected" block in the chapters was copied from these runs.

- `uv run python scripts/smoke_test.py` → `21/21 checks passed` (after switching httpx to an explicit `ssl.create_default_context(cafile=...)`, no warnings).
- Every chapter command was executed, including: the wire tap over HTTP/1.1, plaintext HTTP/2 (preface, SETTINGS, HEADERS/DATA on stream 1) and TLS (only `localhost` SNI and `h2` ALPN readable; `Select-String Ada` → 0 matches); `multiplex.py` (one connection, streams 1/3/5); `wire_format.py`; renumbering a proto field (`0a` → `3a`) and restoring it; all streaming commands; each TLS failure; `certs.py rotate server` + restart (serial changed, clients unaffected); mTLS with server-log diagnosis (`PEER_DID_NOT_RETURN_A_CERTIFICATE`, `CERTIFICATE_VERIFY_FAILED`); the five debugging-clinic cases; deadlines; the full challenge fixed to `6/6 passed` and the two documented "shortcut" fixes rejected.
- `examples/latency_compare.py` results in chapter 12 are labelled as this machine's measurements.
- Docker-only path: `toolbox` ran the gRPC client (TLS and mTLS), `curl` and `openssl s_client` (`ALPN protocol: h2`, `Verify return code: 0`), `plaintext_loopback.py`, and generated and verified a full certificate set with its own OpenSSL.
- Graceful shutdown: `docker compose stop grpc-server` → `received SIGTERM, shutting down (grace 5.0s)`, `stopped`, exit code 0.
- Images: no `/app/certs/out` and no `*.key`/`*.p12` files in `grpc-demo-service`, `grpc-demo-web` or `grpc-demo-toolbox`.
- Dependency audit: `uvx pip-audit==2.10.1` over the exported runtime requirements → `No known vulnerabilities found`.

## 5. Found and fixed during validation

Real problems the runs exposed, all fixed:

- `localhost` resolves to `::1` first; with servers bound or published only on `127.0.0.1`, gRPC reported a misleading IPv6 "connection refused" instead of the TLS error. Servers now bind `localhost` (both stacks) and Compose publishes on `127.0.0.1` and `[::1]`.
- Windows' cp1252 console could not print the Hindi greeting; the CLIs now write UTF-8.
- Windows Schannel curl fails revocation checks for a local CA; documented `--ssl-revoke-best-effort` (verification stays on) and made the Python client the primary path.
- On Windows a rejected client certificate shows `Connection aborted` rather than `End of TCP stream`; diagnosis handles both.
- PowerShell 5.1 mangles embedded JSON quotes for native programs; the REST client gained `--name/--language/--delay-ms`.
- FastAPI turned an exception raised inside `receive()` into a 400; the body-size limit now buffers and rejects with 413 before the app runs.
- Health-check calls flooded the server log; they are still counted but no longer logged.
- A CI step scanning images for keys matched the OS's public CA bundle; it now looks for the workshop directory and private-key files only.
- jsdom 30 requires Node ≥ 22.14; pinned jsdom 26.1.0 so the frontend tests run on every Node 22 release.
- The repository's own docs tripped the "never disable verification" test; the wording was made explicit.

## 6. CI and remaining gaps

- **GitHub Actions:** the first CI run on `main` (run 38913256115, ubuntu-latest) passed every job: Python lint/types/proto and `131 passed` (the POSIX key-permission test included, nothing skipped), website checks and build, Compose configuration, and the full stack job - containers running as the runner's UID with `0600` keys, image key scan, `21/21` smoke checks, `21 passed` integration tests, the Docker challenge, graceful shutdown.
- **macOS** was not tested.
- **Deployment** to Vercel and the `grpc.jishanahmed.in` DNS record have not been set up; see [deployment.md](deployment.md).
- The **interactive** `chat` mode (typing on stdin) was verified with piped input, not with a human at a terminal.
