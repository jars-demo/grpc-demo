"""Generate the Python gRPC bindings from services/proto into services/generated.

Usage:
    uv run python scripts/generate_proto.py           # regenerate
    uv run python scripts/generate_proto.py --check   # fail if the committed bindings are stale

Uses the protoc compiler bundled with grpcio-tools, so no separate protoc install is needed.
The generated files are committed so the services run without grpcio-tools; CI runs --check to
prove they match the .proto contract.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO_ROOT = ROOT / "services" / "proto"
OUT_ROOT = ROOT / "services" / "generated"


def _proto_files() -> list[Path]:
    return sorted(PROTO_ROOT.rglob("*.proto"))


def generate(out_dir: Path) -> None:
    from grpc_tools import protoc  # dev dependency, imported lazily for a clear error below

    include = Path(protoc.__file__).parent / "_proto"  # google/protobuf/*.proto
    for proto in _proto_files():
        args = [
            "grpc_tools.protoc",
            f"-I{PROTO_ROOT}",
            f"-I{include}",
            f"--python_out={out_dir}",
            f"--pyi_out={out_dir}",
            f"--grpc_python_out={out_dir}",
            str(proto),
        ]
        if protoc.main(args) != 0:
            raise SystemExit(f"protoc failed for {proto.relative_to(ROOT)}")


def _relative_files(base: Path) -> set[Path]:
    return {
        p.relative_to(base) for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify instead of writing")
    args = parser.parse_args()

    try:
        import grpc_tools  # noqa: F401
    except ImportError:
        print(
            "grpcio-tools is not installed. Run `uv sync` (it is a dev dependency).",
            file=sys.stderr,
        )
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp)
        generate(fresh)
        if args.check:
            expected, actual = _relative_files(fresh), _relative_files(OUT_ROOT)
            stale = sorted(
                str(p)
                for p in expected
                if p not in actual or not filecmp.cmp(fresh / p, OUT_ROOT / p, shallow=False)
            )
            extra = sorted(str(p) for p in actual - expected)
            if stale or extra:
                print(
                    "Generated bindings are out of date. Run: uv run python scripts/generate_proto.py"
                )
                for name in stale:
                    print(f"  stale:   {name}")
                for name in extra:
                    print(f"  unknown: {name}")
                return 1
            print(f"OK: {len(expected)} generated files match {len(_proto_files())} .proto file(s)")
            return 0

        if OUT_ROOT.exists():
            shutil.rmtree(OUT_ROOT)
        shutil.copytree(fresh, OUT_ROOT)
        for path in sorted(_relative_files(OUT_ROOT)):
            print(f"wrote services/generated/{path.as_posix()}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
