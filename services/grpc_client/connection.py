"""How the client connects: target, trust, and (optionally) its own certificate.

Three security modes, chosen explicitly:

    plaintext  no TLS at all. Refused unless the target is a loopback address (chapter 05 only).
    tls        the client verifies the server certificate against a CA and the target hostname.
    mtls       tls + the client presents its own certificate (--cert and --key).

There is no "skip verification" option, by design.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

import grpc

from common.config import is_loopback
from common.tls import channel_credentials

Mode = Literal["plaintext", "tls", "mtls"]


class ConnectionConfigError(Exception):
    pass


@dataclass(frozen=True)
class ConnectionOptions:
    target: str
    ca_file: (
        Path | None
    )  # None = gRPC's bundled public roots (which do not include the workshop CA)
    cert_file: Path | None = None
    key_file: Path | None = None
    plaintext: bool = False
    deadline_seconds: float = 5.0

    @property
    def mode(self) -> Mode:
        if self.plaintext:
            return "plaintext"
        return "mtls" if self.cert_file or self.key_file else "tls"

    @property
    def host(self) -> str:
        host, _, _ = self.target.rpartition(":")
        return host.strip("[]")


def validate(options: ConnectionOptions) -> None:
    if ":" not in options.target:
        raise ConnectionConfigError(f"target {options.target!r} must be host:port")
    if options.plaintext:
        if options.cert_file or options.key_file:
            raise ConnectionConfigError("--plaintext cannot be combined with a client certificate")
        if not is_loopback(options.host):
            raise ConnectionConfigError(
                f"refusing plaintext to {options.host!r}: plaintext is only for the loopback "
                "exercise in chapter 05. Remove --plaintext to use TLS."
            )
    if bool(options.cert_file) != bool(options.key_file):
        raise ConnectionConfigError("mutual TLS needs both --cert and --key")


def open_channel(options: ConnectionOptions) -> grpc.Channel:
    validate(options)
    if options.plaintext:
        return grpc.insecure_channel(options.target)
    creds = channel_credentials(options.ca_file, options.cert_file, options.key_file)
    return grpc.secure_channel(options.target, creds)


# --- Profiles (used by the final challenge) --------------------------------------------------

PROFILE_KEYS = {"target", "ca", "cert", "key", "plaintext", "deadline_seconds"}


def load_profile(path: Path, base: ConnectionOptions) -> ConnectionOptions:
    """Apply a TOML connection profile on top of `base`. Relative paths are relative to the
    current directory, like command-line flags. An empty string clears a file setting."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConnectionConfigError(f"profile not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConnectionConfigError(f"profile {path} is not valid TOML: {exc}") from None
    unknown = set(data) - PROFILE_KEYS
    if unknown:
        raise ConnectionConfigError(
            f"profile {path}: unknown keys {sorted(unknown)}; allowed: {sorted(PROFILE_KEYS)}"
        )

    def _path(key: str, current: Path | None) -> Path | None:
        if key not in data:
            return current
        value = data[key]
        if not isinstance(value, str):
            raise ConnectionConfigError(f"profile {path}: {key} must be a string")
        return Path(value) if value else None

    options = replace(
        base,
        target=str(data.get("target", base.target)),
        ca_file=_path("ca", base.ca_file),
        cert_file=_path("cert", base.cert_file),
        key_file=_path("key", base.key_file),
        plaintext=bool(data.get("plaintext", base.plaintext)),
        deadline_seconds=float(data.get("deadline_seconds", base.deadline_seconds)),
    )
    validate(options)
    return options
