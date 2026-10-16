"""Final challenge runner. Run from the repository root with the Docker stack up.

    uv run python -m challenge start          # copy the broken profiles to challenge/work/
    uv run python -m challenge list
    uv run python -m challenge run 01         # reproduce the failure (real call, real error)
    uv run python -m challenge hint 01        # one more hint each time (3 per scenario)
    uv run python -m challenge check 01       # verify your fix; `check all` for everything
    uv run python -m challenge reset 01       # restore the broken profile

Edit only challenge/work/NN.toml. A fix passes when the call succeeds AND the profile is still
secure: TLS or mutual TLS as the scenario requires, trusting the workshop CA, and a bounded deadline.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import shutil
import sys
from pathlib import Path

from challenge.scenarios import BY_NUMBER, SCENARIOS, Scenario
from grpc_client.__main__ import main as client_main
from grpc_client.connection import ConnectionConfigError, ConnectionOptions, load_profile

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "scenarios"
WORK = HERE / "work"
WORKSHOP_CA = Path("certs/out/ca.crt")


def show(path: Path) -> str:
    """Path relative to the current directory when possible (it can be on another drive)."""
    try:
        return os.path.relpath(path)
    except ValueError:
        return str(path)


def work_profile(s: Scenario) -> Path:
    return WORK / f"{s.number}.toml"


def start(force: bool) -> None:
    WORK.mkdir(exist_ok=True)
    for s in SCENARIOS:
        target = work_profile(s)
        if target.exists() and not force:
            print(f"  kept     {show(target)} (use --force to overwrite)")
            continue
        shutil.copyfile(TEMPLATES / f"{s.number}.toml", target)
        print(f"  created  {show(target)}")
    print("\nNext: python -m challenge run 01")


def run(s: Scenario, quiet: bool = False) -> int:
    profile = work_profile(s)
    if not profile.exists():
        print("No working copy yet. Run: python -m challenge start", file=sys.stderr)
        return 2
    argv = ["--profile", show(profile), "--show-connection", *s.command]
    if not quiet:
        print(f"$ python -m grpc_client {' '.join(argv)}\n", flush=True)
        return client_main(argv)
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        return client_main(argv)


def security_problems(s: Scenario, options: ConnectionOptions) -> list[str]:
    """A connection that 'works' is not enough: reject fixes that weaken security."""
    problems = []
    if options.mode != s.expected_mode:
        problems.append(
            f"this scenario must be solved with {s.expected_mode}, the profile uses {options.mode}"
        )
    if options.ca_file is None:
        problems.append(
            'the profile must trust the workshop CA explicitly (ca = "certs/out/ca.crt")'
        )
    elif not WORKSHOP_CA.exists() or options.ca_file.read_bytes() != WORKSHOP_CA.read_bytes():
        problems.append("the profile must trust exactly the workshop CA, certs/out/ca.crt")
    if s.max_deadline is not None and options.deadline_seconds > s.max_deadline:
        problems.append(
            f"deadline_seconds must stay bounded (at most {s.max_deadline:g} s for this call)"
        )
    return problems


def check(s: Scenario) -> bool:
    profile = work_profile(s)
    base = ConnectionOptions(target="localhost:50051", ca_file=WORKSHOP_CA)
    try:
        options = load_profile(profile, base)
    except ConnectionConfigError as exc:
        print(f"  {s.number} {s.title:<34} FAIL  {exc}")
        return False
    problems = security_problems(s, options)
    if problems:
        print(f"  {s.number} {s.title:<34} FAIL  " + "; ".join(problems))
        return False
    if run(s, quiet=True) != 0:
        print(
            f"  {s.number} {s.title:<34} FAIL  the call still fails: python -m challenge run {s.number}"
        )
        return False
    print(f"  {s.number} {s.title:<34} PASS")
    return True


def hint(s: Scenario) -> None:
    WORK.mkdir(exist_ok=True)
    counter = WORK / f".{s.number}.hints"
    shown = int(counter.read_text()) if counter.exists() else 0
    level = min(shown + 1, len(s.hints))
    counter.write_text(str(level))
    for i in range(level):
        print(f"hint {i + 1}/{len(s.hints)}: {s.hints[i]}")
    if level == len(s.hints):
        print(
            "\nNo more hints. The full solution is in workshop/13-final-challenge.md (Solutions)."
        )


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="python -m challenge", description="Final challenge runner"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    st = sub.add_parser("start", help="create your working copies of the broken profiles")
    st.add_argument("--force", action="store_true")
    sub.add_parser("list", help="list the scenarios")
    for name in ("run", "hint", "reset"):
        p = sub.add_parser(name)
        p.add_argument("number", choices=list(BY_NUMBER))
    ch = sub.add_parser("check", help="verify a fix")
    ch.add_argument("number", choices=[*BY_NUMBER, "all"])
    args = parser.parse_args(argv)

    match args.command:
        case "start":
            start(args.force)
        case "list":
            for s in SCENARIOS:
                state = "ready" if work_profile(s).exists() else "not started"
                print(f"  {s.number}  {s.title:<34} {state:<12} {s.ticket}")
        case "run":
            return run(BY_NUMBER[args.number])
        case "hint":
            hint(BY_NUMBER[args.number])
        case "reset":
            s = BY_NUMBER[args.number]
            WORK.mkdir(exist_ok=True)
            shutil.copyfile(TEMPLATES / f"{s.number}.toml", work_profile(s))
            (WORK / f".{s.number}.hints").unlink(missing_ok=True)
            print(f"restored {show(work_profile(s))}")
        case "check":
            chosen = SCENARIOS if args.number == "all" else (BY_NUMBER[args.number],)
            passed = sum(check(s) for s in chosen)
            print(f"\n{passed}/{len(chosen)} passed")
            return 0 if passed == len(chosen) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
