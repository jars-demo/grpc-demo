# Contributing

Thanks for helping improve **gRPC & HTTPS**. This is a teaching project: correctness, clarity and honest output matter more than features.

## Before you start

- Read [AGENTS.md](AGENTS.md): its rules apply to every change, human or AI.
- For anything larger than a fix, [open an issue](https://github.com/jars-demo/grpc-demo/issues) first and describe the learning goal.

## Set up

```bash
git clone https://github.com/jars-demo/grpc-demo.git
cd grpc-demo
uv run python scripts/tasks.py setup     # uv sync, npm ci, certificates
uv run python scripts/tasks.py up
uv run python scripts/tasks.py smoke-test
```

Prerequisites and per-OS notes: [README.md](README.md#prerequisites).

## Make a change

1. Branch from `main`.
2. Keep the change focused; add or update tests for any behaviour change.
3. Changed the `.proto`? Run `uv run python scripts/generate_proto.py` and commit the generated files too.
4. Changed a command, port, path, error message or output? Update the chapters, docs and README in the same change, **re-run every affected command**, and paste real output. Never write expected output by hand.
5. Run the checks:

   ```bash
   uv run python scripts/tasks.py check          # Python lint, types, proto, tests + website
   uv run python scripts/tasks.py up
   uv run python scripts/tasks.py smoke-test
   uv run python scripts/tasks.py test-integration
   ```

6. Open a pull request using the template; list the commands you ran and their results.

## Writing chapters

Each chapter in `workshop/` starts with:

```markdown
# NN · Title

> ⏱ N minutes · One-line summary.
```

and contains, in order: Learning objectives, Prerequisites, Concept, Exercise (exact commands + **Expected** output), What just happened, Common failure, Knowledge check (answers in `<details>`), Done when. `frontend/test/content.test.ts` enforces the structure and checks that relative links resolve. Explain in plain language first, then add precise detail. Commands must work in PowerShell and bash, or show both variants.

## Security

Never add a way to skip certificate verification, never commit keys (even workshop ones), and keep plaintext loopback-only. See [docs/security.md](docs/security.md). Report concerns via an issue without including key material.

## Commits

Use clear, imperative commit messages that explain *why*, for example `Explain SNI visibility in chapter 08`. Keep unrelated changes in separate commits.

## License

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).
