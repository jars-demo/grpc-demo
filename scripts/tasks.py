"""Cross-platform task runner: the same commands on Windows (PowerShell), macOS and Linux.

    python scripts/tasks.py <task> [args...]
    make <task>                                  # if you have make: a thin wrapper around this file

Tasks:
    setup             uv sync, npm ci (frontend), generate certificates
    certs             generate certificates (no-op if they exist; see certs/scripts/certs.py)
    generate-proto    regenerate services/generated from services/proto
    lint              ruff check + ruff format --check + proto consistency
    format            ruff format + ruff check --fix
    typecheck         mypy (strict)
    test              unit, gRPC, TLS and security tests (no Docker needed)
    test-integration  tests against the running Docker stack
    frontend-check    lint, typecheck, tests and static build of the website
    check             lint + typecheck + test (+ frontend-check if node_modules exists)
    up                build and start the stack, wait until healthy
    down              stop the stack
    logs [service]    follow container logs
    smoke-test        end-to-end checks against the running stack
    clean             remove caches, build output and challenge working copies (not certificates)

Only the standard library is used, so `python scripts/tasks.py` works before `uv sync`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


class TaskError(Exception):
    pass


def need(tool: str, why: str) -> str:
    path = shutil.which(tool)
    if path is None:
        raise TaskError(
            f"`{tool}` is not on PATH; it is needed to {why}. See README.md > Prerequisites."
        )
    return path


def sh(*args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print(f"\n$ {' '.join(args)}", flush=True)
    exe = need(args[0], f"run `{' '.join(args[:2])}`")
    result = subprocess.run([exe, *args[1:]], cwd=cwd, env=env, check=False)
    if result.returncode != 0:
        raise TaskError(f"`{' '.join(args)}` exited with {result.returncode}")


def uv_run(*args: str) -> None:
    sh("uv", "run", *args)


def compose_env() -> dict[str, str]:
    """On Linux/macOS, run containers as the current user so they can read the 0600 key files.
    Docker Desktop on Windows maps bind-mount permissions itself and needs nothing."""
    env = dict(os.environ)
    if sys.platform != "win32":
        env.setdefault("LOCAL_UID", str(os.getuid()))
        env.setdefault("LOCAL_GID", str(os.getgid()))
    return env


# --- tasks -----------------------------------------------------------------------------------


def setup() -> None:
    sh("uv", "sync")
    if shutil.which("npm"):
        sh("npm", "ci", "--no-audit", "--no-fund", cwd=FRONTEND)
    else:
        print("npm not found: skipping the frontend (only needed for the website)")
    certs()
    print("\nSetup complete. Next: python scripts/tasks.py up")


def certs() -> None:
    uv_run("python", "certs/scripts/certs.py", "generate")


def generate_proto() -> None:
    uv_run("python", "scripts/generate_proto.py")


def lint() -> None:
    uv_run("ruff", "check", ".")
    uv_run("ruff", "format", "--check", ".")
    uv_run("python", "scripts/generate_proto.py", "--check")


def fmt() -> None:
    uv_run("ruff", "format", ".")
    uv_run("ruff", "check", "--fix", ".")


def typecheck() -> None:
    uv_run("mypy")


def test() -> None:
    uv_run("pytest")


def test_integration() -> None:
    uv_run("pytest", "-m", "integration", "tests/integration")


def frontend_check() -> None:
    for script in ("lint", "typecheck", "format:check", "test", "build"):
        sh("npm", "run", script, cwd=FRONTEND)


def check() -> None:
    lint()
    typecheck()
    test()
    if (FRONTEND / "node_modules").exists():
        frontend_check()
    else:
        print("\nfrontend/node_modules missing: skipped frontend checks (run setup)")


def up() -> None:
    missing = [
        n
        for n in ("ca.crt", "server.crt", "server.key", "expired-server.crt")
        if not (ROOT / "certs" / "out" / n).exists()
    ]
    if missing:
        raise TaskError(
            f"certificates missing ({', '.join(missing)}). Generate them first:\n"
            "  python scripts/tasks.py certs\n"
            "  or without openssl: docker compose --profile tools run --rm --no-deps toolbox python certs/scripts/certs.py generate"
        )
    sh("docker", "compose", "up", "--build", "--detach", "--wait", env=compose_env())
    sh("docker", "compose", "ps", env=compose_env())


def down() -> None:
    sh("docker", "compose", "down", env=compose_env())


def logs(*services: str) -> None:
    sh("docker", "compose", "logs", "--follow", "--tail", "100", *services, env=compose_env())


def smoke_test() -> None:
    uv_run("python", "scripts/smoke_test.py")


def clean() -> None:
    patterns = [
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "frontend/.next",
        "frontend/out",
        "challenge/work",
    ]
    for rel in patterns:
        path = ROOT / rel
        if path.exists():
            shutil.rmtree(path)
            print(f"removed {rel}")
    for cache in ROOT.rglob("__pycache__"):
        if ".venv" not in cache.parts and "node_modules" not in cache.parts:
            shutil.rmtree(cache)
    print("Certificates are kept. To remove them: uv run python certs/scripts/certs.py clean")


TASKS: dict[str, Callable[..., None]] = {
    "setup": setup,
    "certs": certs,
    "generate-proto": generate_proto,
    "lint": lint,
    "format": fmt,
    "typecheck": typecheck,
    "test": test,
    "test-integration": test_integration,
    "frontend-check": frontend_check,
    "check": check,
    "up": up,
    "down": down,
    "logs": logs,
    "smoke-test": smoke_test,
    "clean": clean,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in TASKS:
        print(__doc__)
        return 0 if not argv else 2
    try:
        TASKS[argv[0]](*argv[1:])
    except TaskError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
