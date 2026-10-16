from __future__ import annotations

from pathlib import Path

import grpc
import pytest

from grpc_client.connection import ConnectionConfigError, ConnectionOptions, load_profile, validate
from grpc_client.diagnose import diagnose

BASE = ConnectionOptions(target="localhost:50051", ca_file=Path("certs/out/ca.crt"))


def test_plaintext_to_remote_host_is_refused() -> None:
    with pytest.raises(ConnectionConfigError, match="refusing plaintext"):
        validate(ConnectionOptions(target="example.com:50050", ca_file=None, plaintext=True))


def test_plaintext_with_client_certificate_is_refused() -> None:
    with pytest.raises(ConnectionConfigError, match="cannot be combined"):
        validate(
            ConnectionOptions(
                target="localhost:1",
                ca_file=None,
                plaintext=True,
                cert_file=Path("c"),
                key_file=Path("k"),
            )
        )


def test_mtls_requires_both_cert_and_key() -> None:
    with pytest.raises(ConnectionConfigError, match="both --cert and --key"):
        validate(ConnectionOptions(target="localhost:1", ca_file=None, cert_file=Path("c")))


def test_mode_is_derived_from_options() -> None:
    assert BASE.mode == "tls"
    assert (
        ConnectionOptions(target="x:1", ca_file=None, cert_file=Path("c"), key_file=Path("k")).mode
        == "mtls"
    )


def test_profile_overrides_base_and_empty_string_clears_a_path(tmp_path: Path) -> None:
    profile = tmp_path / "p.toml"
    profile.write_text('target = "localhost:50052"\nca = ""\ncert = "a.crt"\nkey = "a.key"\n')

    options = load_profile(profile, BASE)

    assert options.target == "localhost:50052"
    assert options.ca_file is None
    assert options.mode == "mtls"


def test_profile_rejects_unknown_keys(tmp_path: Path) -> None:
    profile = tmp_path / "p.toml"
    profile.write_text('target = "localhost:1"\nverify = false\n')

    with pytest.raises(ConnectionConfigError, match="unknown keys"):
        load_profile(profile, BASE)


class FakeRpcError(grpc.RpcError):
    def __init__(self, code: grpc.StatusCode, details: str) -> None:
        self._code, self._details = code, details

    def code(self) -> grpc.StatusCode:
        return self._code

    def details(self) -> str:
        return self._details


@pytest.mark.parametrize(
    ("details", "expected"),
    [
        ("...CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate", "chain"),
        ("...Hostname Verification Check failed.", "Subject Alternative Name"),
        ("...ipv4:127.0.0.1:50052: End of TCP stream", "client sent no certificate"),
        ("...WRONG_VERSION_NUMBER...", "does not speak TLS"),
        ("...Connection refused", "Nothing is listening"),
        ("errors resolving grpc-server:50051: ...", "only resolve inside the Compose network"),
        ("...CERTIFICATE_VERIFY_FAILED: certificate has expired", "validity period"),
    ],
)
def test_diagnose_explains_connection_failures(details: str, expected: str) -> None:
    diagnosis = diagnose(FakeRpcError(grpc.StatusCode.UNAVAILABLE, details))

    assert len(diagnosis.hints) == 1
    assert expected in diagnosis.hints[0]


def test_diagnose_explains_permission_denied_without_connection_hint() -> None:
    diagnosis = diagnose(FakeRpcError(grpc.StatusCode.PERMISSION_DENIED, "not authorized"))

    assert "not authorization" in diagnosis.meaning
    assert diagnosis.hints == ()
