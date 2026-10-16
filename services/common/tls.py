"""Loading certificate files and building gRPC credentials.

There is deliberately no option here to skip certificate verification. gRPC's Python API does not
offer one for secure channels either: `grpc.ssl_channel_credentials` always verifies the server's
chain and hostname. If a connection fails, fix the certificates, not the verification.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import grpc

CERTS_HINT = (
    "Generate the workshop certificates with: uv run python certs/scripts/certs.py generate"
)


class CertificateFileError(Exception):
    """A certificate or key file is missing or unreadable."""


def read_pem(path: Path, what: str) -> bytes:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise CertificateFileError(f"{what} not found: {path}\n{CERTS_HINT}") from None
    except OSError as exc:
        raise CertificateFileError(f"cannot read {what} {path}: {exc.strerror}") from None
    if b"-----BEGIN" not in data:
        raise CertificateFileError(f"{what} {path} is not a PEM file")
    return data


# --- Server side -----------------------------------------------------------------------------


def server_credentials(
    cert_file: Path, key_file: Path, client_ca_file: Path | None = None
) -> grpc.ServerCredentials:
    """TLS server credentials. With `client_ca_file`, clients MUST present a certificate signed by
    that CA (mutual TLS); the handshake fails otherwise."""
    pair = (read_pem(key_file, "server private key"), read_pem(cert_file, "server certificate"))
    if client_ca_file is None:
        return grpc.ssl_server_credentials([pair])
    return grpc.ssl_server_credentials(
        [pair],
        root_certificates=read_pem(client_ca_file, "client CA certificate"),
        require_client_auth=True,
    )


# --- Client side -----------------------------------------------------------------------------


def channel_credentials(
    ca_file: Path | None,
    client_cert_file: Path | None = None,
    client_key_file: Path | None = None,
) -> grpc.ChannelCredentials:
    """TLS channel credentials that verify the server against `ca_file`.

    `ca_file=None` means "use gRPC's bundled public root CAs", which do NOT include the workshop CA:
    that is exactly the "untrusted CA" exercise. A client certificate is sent only when both the
    certificate and the key are given (mutual TLS).
    """
    if (client_cert_file is None) != (client_key_file is None):
        raise CertificateFileError("mutual TLS needs both a client certificate and its private key")
    root = read_pem(ca_file, "CA certificate") if ca_file else None
    if client_cert_file and client_key_file:
        return grpc.ssl_channel_credentials(
            root_certificates=root,
            private_key=read_pem(client_key_file, "client private key"),
            certificate_chain=read_pem(client_cert_file, "client certificate"),
        )
    return grpc.ssl_channel_credentials(root_certificates=root)


# --- Peer identity ---------------------------------------------------------------------------


# grpc returns {property name: [bytes, ...]}; the stubs type the values loosely, hence Any.
def transport_security(auth_context: Mapping[str, Any]) -> str:
    """'plaintext', 'tls' or 'mtls', derived from the connection's auth context."""
    security = auth_context.get("transport_security_type", [b""])
    if not security or security[0] != b"ssl":
        return "plaintext"
    return "mtls" if client_identity(auth_context) else "tls"


def client_identity(auth_context: Mapping[str, Any]) -> str:
    """The Common Name of the verified client certificate, or '' when there is none.

    gRPC only fills x509_common_name after it has verified the certificate chain against the
    server's client CA, so this value is authenticated - but it is an identity, not a permission.
    """
    names = auth_context.get("x509_common_name") or []
    return names[0].decode("utf-8", "replace") if names else ""
