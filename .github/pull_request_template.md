## What and why

<!-- What does this change, and which learning goal or problem does it serve? -->

## How it was verified

<!-- Paste the commands you ran and their results. If a chapter command or its output changed,
     say which chapter and confirm you re-ran it. -->

- [ ] `uv run python scripts/tasks.py check` passes
- [ ] Integration: `tasks.py up` + `tasks.py smoke-test` pass (if services, Compose or certificates changed)
- [ ] Chapters, README and docs updated for any changed command, port, path or output
- [ ] No certificate verification disabled, no keys or secrets committed
