"""All configuration, in one place.

This is the only module that reads environment variables. Every setting is validated when it is
loaded, so a typo fails at startup with a clear message instead of halfway through a request.
Each variable is documented in .env.example.
"""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Port = Annotated[int, Field(ge=0, le=65535)]
LOOPBACK_NAMES = {"localhost"}


class ConfigError(Exception):
    """Raised with a human-readable list of every invalid setting."""


def is_loopback(host: str) -> bool:
    if host.lower() in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class _Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GrpcServerSettings(_Settings):
    # "localhost" binds both 127.0.0.1 and ::1. Containers set 0.0.0.0.
    bind_host: str = "localhost"
    # 0 disables a listener. Plaintext is off unless explicitly enabled, and only on loopback.
    plaintext_port: Port = 0
    tls_port: Port = 50051
    mtls_port: Port = 50052
    server_cert_file: Path = Path("certs/out/server.crt")
    server_key_file: Path = Path("certs/out/server.key")
    client_ca_file: Path = Path("certs/out/ca.crt")
    max_workers: int = Field(default=16, ge=1, le=256)
    max_message_bytes: int = Field(default=64 * 1024, ge=1024, le=4 * 1024 * 1024)
    shutdown_grace_seconds: float = Field(default=5.0, ge=0, le=60)
    admin_identities: frozenset[str] = frozenset({"workshop-admin"})
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def _check(self) -> GrpcServerSettings:
        if not (self.plaintext_port or self.tls_port or self.mtls_port):
            raise ValueError("enable at least one listener (plaintext, TLS or mTLS port)")
        if self.plaintext_port and not is_loopback(self.bind_host):
            raise ValueError(
                f"plaintext gRPC is only allowed on a loopback address, not {self.bind_host!r}; "
                "use the TLS listener for anything reachable from another machine or container"
            )
        ports = [p for p in (self.plaintext_port, self.tls_port, self.mtls_port) if p]
        if len(ports) != len(set(ports)):
            raise ValueError("plaintext, TLS and mTLS listeners must use different ports")
        return self

    @property
    def needs_certificates(self) -> bool:
        return bool(self.tls_port or self.mtls_port)


class RestSettings(_Settings):
    bind_host: str = "127.0.0.1"
    port: Port = 8080
    # Both set: serve HTTPS. Both empty: serve plain HTTP.
    tls_cert_file: Path | None = None
    tls_key_file: Path | None = None
    max_body_bytes: int = Field(default=16 * 1024, ge=256, le=1024 * 1024)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def _check(self) -> RestSettings:
        if (self.tls_cert_file is None) != (self.tls_key_file is None):
            raise ValueError("set both REST_TLS_CERT_FILE and REST_TLS_KEY_FILE, or neither")
        return self

    @property
    def tls_enabled(self) -> bool:
        return self.tls_cert_file is not None


class ClientSettings(_Settings):
    """Defaults for the command-line clients. Command-line flags override them."""

    target: str = "localhost:50051"
    ca_file: Path = Path("certs/out/ca.crt")
    client_cert_file: Path | None = None
    client_key_file: Path | None = None
    deadline_seconds: float = Field(default=5.0, gt=0, le=300)
    rest_base_url: str = "https://localhost:8443"

    @field_validator("target")
    @classmethod
    def _target(cls, value: str) -> str:
        if ":" not in value:
            raise ValueError("target must be host:port, for example localhost:50051")
        return value


# --- Loading ---------------------------------------------------------------------------------

_GRPC_SERVER_ENV = {
    "GRPC_BIND_HOST": "bind_host",
    "GRPC_PLAINTEXT_PORT": "plaintext_port",
    "GRPC_TLS_PORT": "tls_port",
    "GRPC_MTLS_PORT": "mtls_port",
    "GRPC_SERVER_CERT_FILE": "server_cert_file",
    "GRPC_SERVER_KEY_FILE": "server_key_file",
    "GRPC_CLIENT_CA_FILE": "client_ca_file",
    "GRPC_MAX_WORKERS": "max_workers",
    "GRPC_MAX_MESSAGE_BYTES": "max_message_bytes",
    "GRPC_SHUTDOWN_GRACE_SECONDS": "shutdown_grace_seconds",
    "GRPC_ADMIN_IDENTITIES": "admin_identities",
    "LOG_LEVEL": "log_level",
}
_REST_ENV = {
    "REST_BIND_HOST": "bind_host",
    "REST_PORT": "port",
    "REST_TLS_CERT_FILE": "tls_cert_file",
    "REST_TLS_KEY_FILE": "tls_key_file",
    "REST_MAX_BODY_BYTES": "max_body_bytes",
    "LOG_LEVEL": "log_level",
}
_CLIENT_ENV = {
    "GRPC_TARGET": "target",
    "GRPC_CA_FILE": "ca_file",
    "GRPC_CLIENT_CERT_FILE": "client_cert_file",
    "GRPC_CLIENT_KEY_FILE": "client_key_file",
    "GRPC_DEADLINE_SECONDS": "deadline_seconds",
    "REST_BASE_URL": "rest_base_url",
}
_LIST_FIELDS = {"admin_identities"}


def _collect(env: Mapping[str, str], mapping: dict[str, str]) -> dict[str, object]:
    values: dict[str, object] = {}
    for var, field in mapping.items():
        raw = env.get(var)
        if raw is None or raw.strip() == "":
            continue
        raw = raw.strip()
        values[field] = (
            frozenset(p.strip() for p in raw.split(",") if p.strip())
            if field in _LIST_FIELDS
            else raw
        )
    return values


def _load[T: _Settings](
    model: type[T], env: Mapping[str, str], mapping: dict[str, str], **overrides: Any
) -> T:
    values = _collect(env, mapping)
    values.update({k: v for k, v in overrides.items() if v is not None})
    try:
        return model.model_validate(values)
    except ValidationError as exc:
        reverse = {field: var for var, field in mapping.items()}
        lines = []
        for err in exc.errors():
            field = str(err["loc"][0]) if err["loc"] else ""
            name = reverse.get(field, field or model.__name__)
            lines.append(f"  {name}: {err['msg']}")
        raise ConfigError("Invalid configuration:\n" + "\n".join(lines)) from None


def load_grpc_server_settings(
    env: Mapping[str, str] | None = None, **overrides: Any
) -> GrpcServerSettings:
    return _load(
        GrpcServerSettings, os.environ if env is None else env, _GRPC_SERVER_ENV, **overrides
    )


def load_rest_settings(env: Mapping[str, str] | None = None, **overrides: Any) -> RestSettings:
    return _load(RestSettings, os.environ if env is None else env, _REST_ENV, **overrides)


def load_client_settings(env: Mapping[str, str] | None = None, **overrides: Any) -> ClientSettings:
    return _load(ClientSettings, os.environ if env is None else env, _CLIENT_ENV, **overrides)
