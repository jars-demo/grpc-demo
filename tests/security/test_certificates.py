"""The generated certificates have the properties the exercises depend on, and regenerating them
produces the same structure (reproducible), while keys are never reused."""

from __future__ import annotations

import os
import ssl
import subprocess
from pathlib import Path

import pytest

from certs.scripts import certs as certs_tool


def x509(path: Path, *flags: str) -> str:
    result = subprocess.run(
        ["openssl", "x509", "-in", str(path), "-noout", *flags],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def verify(certs_dir: Path, name: str, purpose: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "openssl",
            "verify",
            "-CAfile",
            str(certs_dir / "ca.crt"),
            "-purpose",
            purpose,
            str(certs_dir / f"{name}.crt"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_ca_is_a_ca_and_is_labelled_educational(certs_dir: Path) -> None:
    text = x509(certs_dir / "ca.crt", "-subject", "-ext", "basicConstraints,keyUsage")
    assert "CA:TRUE" in text
    assert "Certificate Sign" in text
    assert "Local educational CA" in text


def test_server_certificate_has_dns_sans_and_no_ip_san(certs_dir: Path) -> None:
    san = x509(certs_dir / "server.crt", "-ext", "subjectAltName")
    assert "DNS:localhost" in san and "DNS:grpc-server" in san and "DNS:rest-https" in san
    assert "IP Address" not in san  # chapter 09's hostname exercise depends on this


def test_server_certificate_is_server_auth_only_and_not_a_ca(certs_dir: Path) -> None:
    text = x509(certs_dir / "server.crt", "-ext", "basicConstraints,extendedKeyUsage")
    assert "CA:FALSE" in text
    assert "TLS Web Server Authentication" in text
    assert "Client Authentication" not in text


@pytest.mark.parametrize("name", ["client", "admin"])
def test_client_certificates_are_client_auth_only(certs_dir: Path, name: str) -> None:
    text = x509(certs_dir / f"{name}.crt", "-ext", "extendedKeyUsage")
    assert "TLS Web Client Authentication" in text
    assert "Server Authentication" not in text
    assert verify(certs_dir, name, "sslserver").returncode != 0  # cannot be used as a server


def test_server_and_clients_verify_against_workshop_ca(certs_dir: Path) -> None:
    assert verify(certs_dir, "server", "sslserver").returncode == 0
    assert verify(certs_dir, "client", "sslclient").returncode == 0
    assert verify(certs_dir, "admin", "sslclient").returncode == 0


def test_expired_certificate_fails_verification_with_expiry_reason(certs_dir: Path) -> None:
    result = verify(certs_dir, "expired-server", "sslserver")
    assert result.returncode != 0
    assert "certificate has expired" in result.stdout + result.stderr


def test_rogue_client_has_same_name_but_untrusted_issuer(certs_dir: Path) -> None:
    assert "CN=workshop-client" in x509(
        certs_dir / "rogue-client.crt", "-subject", "-nameopt", "RFC2253"
    )
    assert verify(certs_dir, "rogue-client", "sslclient").returncode != 0


def test_leaf_validity_is_90_days(certs_dir: Path) -> None:
    cert = ssl._ssl._test_decode_cert(str(certs_dir / "server.crt"))  # type: ignore[attr-defined]
    days = (
        ssl.cert_time_to_seconds(cert["notAfter"]) - ssl.cert_time_to_seconds(cert["notBefore"])
    ) / 86400
    assert days == 90


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_private_keys_are_owner_only(certs_dir: Path) -> None:
    for key in certs_dir.glob("*.key"):
        assert key.stat().st_mode & 0o077 == 0, key.name


def test_tool_verify_command_reports_expected_outcomes(certs_dir: Path) -> None:
    assert certs_tool.main(["--out", str(certs_dir), "verify"]) == 0


def test_regeneration_is_structurally_identical_but_uses_fresh_keys(
    tmp_path: Path, certs_dir: Path
) -> None:
    assert certs_tool.main(["--out", str(tmp_path), "generate"]) == 0
    for name in ("server", "client", "admin", "expired-server", "rogue-client"):
        fields = ("-subject", "-ext", "basicConstraints,keyUsage,extendedKeyUsage,subjectAltName")
        assert x509(tmp_path / f"{name}.crt", *fields) == x509(
            certs_dir / f"{name}.crt", *fields
        ), name
        assert (tmp_path / f"{name}.key").read_bytes() != (certs_dir / f"{name}.key").read_bytes()


def test_rotation_issues_new_serial_and_key_that_still_verifies(tmp_path: Path) -> None:
    assert certs_tool.main(["--out", str(tmp_path), "generate"]) == 0
    serial_before = x509(tmp_path / "server.crt", "-serial")
    key_before = (tmp_path / "server.key").read_bytes()

    assert certs_tool.main(["--out", str(tmp_path), "rotate", "server"]) == 0

    assert x509(tmp_path / "server.crt", "-serial") != serial_before
    assert (tmp_path / "server.key").read_bytes() != key_before
    assert verify(tmp_path, "server", "sslserver").returncode == 0
