from __future__ import annotations

from pathlib import Path

import pytest

from common.config import (
    ConfigError,
    is_loopback,
    load_client_settings,
    load_grpc_server_settings,
    load_rest_settings,
)


def test_server_defaults_are_tls_and_mtls_without_plaintext() -> None:
    settings = load_grpc_server_settings({})
    assert (settings.plaintext_port, settings.tls_port, settings.mtls_port) == (0, 50051, 50052)


def test_server_reads_environment_variables() -> None:
    settings = load_grpc_server_settings(
        {
            "GRPC_TLS_PORT": "6000",
            "GRPC_ADMIN_IDENTITIES": "a, b ,",
            "GRPC_SERVER_CERT_FILE": "x.crt",
        }
    )
    assert settings.tls_port == 6000
    assert settings.admin_identities == frozenset({"a", "b"})
    assert settings.server_cert_file == Path("x.crt")


def test_plaintext_is_refused_on_non_loopback_bind_address() -> None:
    with pytest.raises(ConfigError, match="only allowed on a loopback"):
        load_grpc_server_settings({"GRPC_BIND_HOST": "0.0.0.0", "GRPC_PLAINTEXT_PORT": "50050"})


def test_plaintext_is_allowed_on_loopback() -> None:
    settings = load_grpc_server_settings(
        {"GRPC_BIND_HOST": "127.0.0.1", "GRPC_PLAINTEXT_PORT": "50050"}
    )
    assert settings.plaintext_port == 50050


def test_listeners_must_use_distinct_ports() -> None:
    with pytest.raises(ConfigError, match="different ports"):
        load_grpc_server_settings({"GRPC_TLS_PORT": "7000", "GRPC_MTLS_PORT": "7000"})


def test_at_least_one_listener_is_required() -> None:
    with pytest.raises(ConfigError, match="at least one listener"):
        load_grpc_server_settings({"GRPC_TLS_PORT": "0", "GRPC_MTLS_PORT": "0"})


def test_invalid_value_error_names_the_environment_variable() -> None:
    with pytest.raises(ConfigError, match="GRPC_TLS_PORT"):
        load_grpc_server_settings({"GRPC_TLS_PORT": "not-a-number"})


def test_rest_requires_cert_and_key_together() -> None:
    with pytest.raises(ConfigError, match="both"):
        load_rest_settings({"REST_TLS_CERT_FILE": "server.crt"})


def test_rest_tls_enabled_when_both_files_set() -> None:
    assert load_rest_settings({"REST_TLS_CERT_FILE": "a", "REST_TLS_KEY_FILE": "b"}).tls_enabled


def test_client_target_must_include_port() -> None:
    with pytest.raises(ConfigError, match="host:port"):
        load_client_settings({"GRPC_TARGET": "localhost"})


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("localhost", True),
        ("127.0.0.1", True),
        ("::1", True),
        ("0.0.0.0", False),
        ("example.com", False),
    ],
)
def test_is_loopback(host: str, expected: bool) -> None:
    assert is_loopback(host) is expected
