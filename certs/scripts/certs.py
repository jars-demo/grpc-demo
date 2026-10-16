"""The workshop certificate lab: generate, inspect, verify, rotate and clean local certificates.

    uv run python certs/scripts/certs.py generate          # create everything in certs/out/
    uv run python certs/scripts/certs.py list              # what exists, who issued it, expiry
    uv run python certs/scripts/certs.py inspect server    # subject, issuer, validity, SAN, EKU
    uv run python certs/scripts/certs.py verify            # check every leaf against the CA
    uv run python certs/scripts/certs.py rotate server     # new key + certificate, same CA
    uv run python certs/scripts/certs.py regenerate        # clean + generate (new CA too)
    uv run python certs/scripts/certs.py clean             # delete certs/out/

Only the Python standard library and the `openssl` command-line tool are needed. Every openssl
command is printed before it runs, so you can see (and repeat) exactly what happens.

EVERYTHING HERE IS FOR LOCAL EDUCATION ONLY. The keys are unencrypted, the CA is not protected by
anything, and none of it must ever be trusted outside this workshop.
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "certs" / "out"
CONFIG = ROOT / "certs" / "openssl" / "ca.cnf"

ORG = "JARS DEMO gRPC Workshop"
CA_DAYS = 365
LEAF_DAYS = 90
# A fixed window in the past for the expiry exercise (YYYYMMDDHHMMSSZ, UTC).
EXPIRED_START, EXPIRED_END = "20240101000000Z", "20240131000000Z"


@dataclass(frozen=True)
class Authority:
    name: str  # file stem: <name>.crt / <name>.key, database in <name>-db/
    common_name: str
    unit: str


@dataclass(frozen=True)
class Leaf:
    name: str
    common_name: str
    issuer: Authority
    extensions: str  # section in ca.cnf
    purpose: str
    expired: bool = False


WORKSHOP_CA = Authority(
    "ca", "JARS Workshop Local CA", "Local educational CA - do not trust outside the workshop"
)
ROGUE_CA = Authority(
    "rogue-ca", "Rogue Untrusted CA", "Deliberately untrusted CA for failure exercises"
)
AUTHORITIES = (WORKSHOP_CA, ROGUE_CA)

LEAVES = (
    Leaf(
        "server",
        "grpc-server",
        WORKSHOP_CA,
        "server_ext",
        "gRPC (TLS + mTLS) and REST HTTPS server",
    ),
    Leaf(
        "expired-server",
        "grpc-expired",
        WORKSHOP_CA,
        "expired_server_ext",
        "server whose validity ended in 2024",
        expired=True,
    ),
    Leaf(
        "client",
        "workshop-client",
        WORKSHOP_CA,
        "client_ext",
        "mTLS client, authenticated but not an admin",
    ),
    Leaf(
        "admin",
        "workshop-admin",
        WORKSHOP_CA,
        "client_ext",
        "mTLS client authorized for AdminService",
    ),
    Leaf(
        "rogue-client",
        "workshop-client",
        ROGUE_CA,
        "client_ext",
        "same name as `client`, signed by the rogue CA",
    ),
)
LEAF_BY_NAME = {leaf.name: leaf for leaf in LEAVES}


class CertError(Exception):
    pass


# --- openssl ---------------------------------------------------------------------------------


def find_openssl() -> str:
    path = shutil.which("openssl")
    if path is None:
        raise CertError(
            "openssl was not found on PATH.\n"
            "  Windows: it ships with Git for Windows (C:\\Program Files\\Git\\usr\\bin) - add that to PATH,\n"
            "           or run this script inside Docker: docker compose --profile tools run --rm toolbox certs generate\n"
            "  macOS:   brew install openssl   (or use the preinstalled LibreSSL-compatible openssl)\n"
            "  Linux:   sudo apt-get install openssl   /   sudo dnf install openssl"
        )
    return path


def run(
    args: list[str], *, ca_dir: Path | None = None, quiet: bool = False, check: bool = True
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if ca_dir is not None:
        env["GRPC_DEMO_CA_DIR"] = ca_dir.as_posix()
    if not quiet:
        shown = " ".join(_display(a) for a in args[1:])
        print(f"  $ openssl {shown}")
    result = subprocess.run(
        [find_openssl(), *args[1:]], capture_output=True, text=True, env=env, check=False
    )
    if check and result.returncode != 0:
        raise CertError(f"openssl {args[1]} failed:\n{result.stderr.strip()}")
    return result


def _display(arg: str) -> str:
    try:
        return Path(arg).relative_to(ROOT).as_posix() if Path(arg).is_absolute() else _quote(arg)
    except ValueError:
        return _quote(arg)


def _quote(arg: str) -> str:
    return f'"{arg}"' if " " in arg else arg


def _protect(key: Path) -> None:
    # Owner read/write only. Effective on Linux/macOS; on Windows, NTFS ACLs of the folder apply.
    key.chmod(0o600)


# --- generation ------------------------------------------------------------------------------


def _subject(common_name: str, unit: str | None = None) -> str:
    parts = [f"/O={ORG}"] + ([f"/OU={unit}"] if unit else []) + [f"/CN={common_name}"]
    return "".join(parts)


def create_authority(out: Path, ca: Authority) -> None:
    db = out / f"{ca.name}-db"
    (db / "newcerts").mkdir(parents=True, exist_ok=True)
    (db / "index.txt").write_text("")
    (db / "serial").write_text(secrets.token_hex(16).upper() + "\n")
    key, crt = out / f"{ca.name}.key", out / f"{ca.name}.crt"
    print(f"\n[{ca.name}] {ca.common_name}")
    run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(key)])
    _protect(key)
    run(
        [
            "openssl",
            "req",
            "-config",
            str(CONFIG),
            "-new",
            "-x509",
            "-key",
            str(key),
            "-sha256",
            "-days",
            str(CA_DAYS),
            "-subj",
            _subject(ca.common_name, ca.unit),
            "-extensions",
            "v3_ca",
            "-out",
            str(crt),
        ],
        ca_dir=db,
    )


def issue_leaf(out: Path, leaf: Leaf) -> None:
    ca = leaf.issuer
    db = out / f"{ca.name}-db"
    key, csr, crt = out / f"{leaf.name}.key", out / f"{leaf.name}.csr", out / f"{leaf.name}.crt"
    print(f"\n[{leaf.name}] CN={leaf.common_name} - {leaf.purpose}")
    run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(key)])
    _protect(key)
    run(
        [
            "openssl",
            "req",
            "-config",
            str(CONFIG),
            "-new",
            "-key",
            str(key),
            "-subj",
            _subject(leaf.common_name),
            "-out",
            str(csr),
        ],
        ca_dir=db,
    )
    validity = (
        ["-startdate", EXPIRED_START, "-enddate", EXPIRED_END]
        if leaf.expired
        else ["-days", str(LEAF_DAYS)]
    )
    run(
        [
            "openssl",
            "ca",
            "-config",
            str(CONFIG),
            "-batch",
            "-notext",
            "-in",
            str(csr),
            "-out",
            str(crt),
            "-cert",
            str(out / f"{ca.name}.crt"),
            "-keyfile",
            str(out / f"{ca.name}.key"),
            "-extensions",
            leaf.extensions,
            *validity,
        ],
        ca_dir=db,
    )
    csr.unlink()


def generate(out: Path, force: bool) -> None:
    find_openssl()
    if (out / "ca.crt").exists() and not force:
        print(
            f"Certificates already exist in {_rel(out)}. Use `regenerate` to start over or `rotate <name>`."
        )
        return
    out.mkdir(parents=True, exist_ok=True)
    (out / "README.txt").write_text(
        "LOCAL EDUCATIONAL CERTIFICATES - generated by certs/scripts/certs.py.\n"
        "Never commit, share, or trust these outside the gRPC & HTTPS workshop.\n"
    )
    for ca in AUTHORITIES:
        create_authority(out, ca)
    for leaf in LEAVES:
        issue_leaf(out, leaf)
    print(f"\nDone. {len(AUTHORITIES)} CAs and {len(LEAVES)} certificates in {_rel(out)}")


def rotate(out: Path, name: str) -> None:
    """Re-issue one leaf with a fresh key from the same CA. Clients keep trusting ca.crt, so only
    the server (or client) that owns the certificate needs a restart to pick it up."""
    leaf = LEAF_BY_NAME.get(name)
    if leaf is None:
        raise CertError(f"unknown certificate {name!r}; choose from: {', '.join(LEAF_BY_NAME)}")
    if not (out / f"{leaf.issuer.name}.crt").exists():
        raise CertError("no CA yet: run `generate` first")
    before = _field(out / f"{name}.crt", "-serial") if (out / f"{name}.crt").exists() else "none"
    issue_leaf(out, leaf)
    print(f"\nRotated {name}: serial {before} -> {_field(out / f'{name}.crt', '-serial')}")
    print("Restart whatever uses it, e.g.: docker compose restart grpc-server rest-https")


# --- inspection ------------------------------------------------------------------------------


def _field(crt: Path, flag: str) -> str:
    result = run(["openssl", "x509", "-in", str(crt), "-noout", flag], quiet=True)
    return result.stdout.strip().split("=", 1)[-1]


def _require(path: Path) -> Path:
    if not path.exists():
        raise CertError(
            f"{_rel(path)} does not exist. Run: uv run python certs/scripts/certs.py generate"
        )
    return path


def inspect(out: Path, name: str) -> None:
    crt = _require(out / f"{name}.crt")
    result = run(
        [
            "openssl",
            "x509",
            "-in",
            str(crt),
            "-noout",
            "-subject",
            "-issuer",
            "-serial",
            "-dates",
            "-ext",
            "basicConstraints,keyUsage,extendedKeyUsage,subjectAltName",
            "-nameopt",
            "RFC2253",
        ]
    )
    print(result.stdout.rstrip())


def list_certs(out: Path) -> None:
    rows = [(ca.name, ca.common_name, "self-signed") for ca in AUTHORITIES]
    rows += [(leaf.name, leaf.common_name, leaf.issuer.name) for leaf in LEAVES]
    print(f"{'file':<20} {'common name':<24} {'issuer':<12} expires")
    for name, cn, issuer in rows:
        crt = out / f"{name}.crt"
        expires = _field(crt, "-enddate") if crt.exists() else "(missing)"
        print(f"{name + '.crt':<20} {cn:<24} {issuer:<12} {expires}")


def verify(out: Path) -> int:
    """Verify every leaf against the workshop CA and report whether the outcome is the expected one."""
    ca = _require(out / "ca.crt")
    failures = 0
    print(f"Verifying against {_rel(ca)} (the workshop CA):\n")
    for leaf in LEAVES:
        crt = _require(out / f"{leaf.name}.crt")
        purpose = "sslclient" if leaf.extensions == "client_ext" else "sslserver"
        result = run(
            ["openssl", "verify", "-CAfile", str(ca), "-purpose", purpose, str(crt)],
            quiet=True,
            check=False,
        )
        ok = result.returncode == 0
        expected_ok = leaf.issuer is WORKSHOP_CA and not leaf.expired
        detail = "OK" if ok else _verify_reason(result.stderr + result.stdout)
        verdict = "as expected" if ok == expected_ok else "UNEXPECTED"
        failures += ok != expected_ok
        print(f"  {leaf.name + '.crt':<20} {detail:<52} [{verdict}]")
    for pem in (out / "server.key", out / "server.crt"):
        _require(pem)
    match = _public_key(out / "server.key", is_key=True) == _public_key(
        out / "server.crt", is_key=False
    )
    failures += not match
    print(f"\n  server.key matches server.crt: {'yes' if match else 'NO'}")
    return 1 if failures else 0


def _verify_reason(output: str) -> str:
    """The human-readable reason from `openssl verify`, e.g. 'certificate has expired'."""
    for line in output.splitlines():
        if "lookup:" in line:
            return "FAIL: " + line.split("lookup:", 1)[1].strip()
    return "FAIL: " + (output.strip().splitlines() or ["unknown error"])[-1]


def _public_key(path: Path, *, is_key: bool) -> str:
    args = (
        ["openssl", "pkey", "-in", str(path), "-pubout"]
        if is_key
        else ["openssl", "x509", "-in", str(path), "-noout", "-pubkey"]
    )
    return run(args, quiet=True).stdout.strip()


def clean(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
        print(f"Removed {_rel(out)}")
    else:
        print(f"Nothing to remove: {_rel(out)} does not exist")


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


# --- CLI -------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="certs.py", description="Workshop certificate lab (local, educational)."
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="output directory (default: certs/out)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="create the CAs and all certificates")
    gen.add_argument("--force", action="store_true", help="overwrite existing files")
    sub.add_parser("regenerate", help="clean, then generate everything (new CA)")
    sub.add_parser("list", help="list certificates and their expiry")
    ins = sub.add_parser("inspect", help="show subject, issuer, validity, SAN and key usage")
    ins.add_argument("name", choices=[ca.name for ca in AUTHORITIES] + list(LEAF_BY_NAME))
    sub.add_parser("verify", help="verify every certificate against the workshop CA")
    rot = sub.add_parser("rotate", help="issue a new key and certificate from the same CA")
    rot.add_argument("name", choices=list(LEAF_BY_NAME))
    sub.add_parser("clean", help="delete the output directory")
    args = parser.parse_args(argv)
    out: Path = args.out.resolve()

    try:
        match args.command:
            case "generate":
                generate(out, args.force)
            case "regenerate":
                clean(out)
                generate(out, force=True)
            case "list":
                list_certs(out)
            case "inspect":
                inspect(out, args.name)
            case "verify":
                return verify(out)
            case "rotate":
                rotate(out, args.name)
            case "clean":
                clean(out)
    except CertError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
