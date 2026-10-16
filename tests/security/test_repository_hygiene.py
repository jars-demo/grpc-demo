"""Guards against the mistakes this workshop teaches you to avoid: disabled verification, insecure
fallbacks, and key material that could end up in Git or in an image."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from common import tls

ROOT = Path(__file__).resolve().parents[2]
CODE_DIRS = (
    "services/common",
    "services/core",
    "services/grpc_server",
    "services/grpc_client",
    "services/rest_api",
    "examples",
    "challenge",
    "scripts",
    "certs/scripts",
)

INSECURE_PATTERNS = {
    r"verify\s*=\s*False": "httpx/requests certificate verification disabled",
    r"check_hostname\s*=\s*False": "ssl hostname checking disabled",
    r"CERT_NONE": "ssl verification disabled",
    r"_create_unverified_context": "unverified ssl context",
    r"ssl_target_name_override": "gRPC hostname override (hides SAN mismatches)",
    r"--insecure|curl -k\b": "curl verification disabled",
}


def python_sources() -> list[Path]:
    return [p for d in CODE_DIRS for p in (ROOT / d).rglob("*.py") if "__pycache__" not in p.parts]


def test_no_code_disables_certificate_verification() -> None:
    offenders = [
        f"{path.relative_to(ROOT)}: {why}"
        for path in python_sources()
        for pattern, why in INSECURE_PATTERNS.items()
        if re.search(pattern, path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_workshop_docs_never_tell_learners_to_disable_verification() -> None:
    offenders = []
    for path in [
        *(ROOT / "workshop").glob("*.md"),
        *(ROOT / "docs").glob("*.md"),
        ROOT / "README.md",
    ]:
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.search(r"\b(never|do not|don't)\b", line, flags=re.IGNORECASE):
                continue  # a warning against the practice, not an instruction to use it
            if re.search(r"curl\b.*\s`?(-k|--insecure)\b|verify\s*=\s*False", line):
                offenders.append(f"{path.relative_to(ROOT)}: {line.strip()[:80]}")
    assert offenders == []


def test_channel_credentials_offer_no_way_to_skip_verification() -> None:
    params = inspect.signature(tls.channel_credentials).parameters
    assert set(params) == {"ca_file", "client_cert_file", "client_key_file"}


def test_gitignore_excludes_generated_certificates_keys_and_env() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for entry in ("certs/out/", "*.key", ".env", "challenge/work/"):
        assert entry in ignored, entry


def test_dockerignore_keeps_keys_out_of_images() -> None:
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for entry in ("certs/out", "**/*.key", ".env"):
        assert entry in ignored, entry


def test_no_private_keys_are_tracked_in_the_repository() -> None:
    skip = {".git", ".venv", "node_modules", "out", ".next", "certs"}
    offenders = [
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file()
        and not skip.intersection(p.relative_to(ROOT).parts)
        and p.suffix in {".py", ".md", ".toml", ".yml", ".yaml", ".ts", ".tsx", ".json", ".txt"}
        and "PRIVATE KEY-----" in p.read_text(encoding="utf-8", errors="ignore")
        and "test_repository_hygiene" not in p.name
    ]
    assert offenders == []


def test_compose_publishes_ports_on_loopback_only() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    published = re.findall(r'^\s*-\s*"([^"]+:\d+)"\s*$', compose, flags=re.MULTILINE)
    assert published, "expected published ports"
    assert all(p.startswith(("127.0.0.1:", "[::1]:")) for p in published), published
