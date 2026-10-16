"""Shared fixtures: real certificates (generated with the workshop's own certs.py into a temporary
directory) and real gRPC servers listening on loopback ports. Nothing is mocked at the network or
TLS level, so these tests exercise the same code paths as the workshop exercises."""

from __future__ import annotations

import os

# gRPC's C core logs every failed handshake at INFO; the TLS tests trigger many on purpose.
# Must be set before grpc is imported.
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")

import shutil
import socket
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import grpc
import pytest

from certs.scripts import certs as certs_tool
from common.config import GrpcServerSettings
from grpc_client.connection import ConnectionOptions, open_channel
from grpc_server.server import RunningServer, build_server


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def certs_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("openssl") is None:
        pytest.fail("openssl is required for the TLS tests (see certs/README.md)")
    out = tmp_path_factory.mktemp("certs")
    assert certs_tool.main(["--out", str(out), "generate"]) == 0
    return out


@dataclass
class Servers:
    plaintext: int
    tls: int
    mtls: int
    certs: Path

    def options(
        self,
        port: int,
        *,
        host: str = "localhost",
        ca: str | None = "ca",
        client: str | None = None,
        plaintext: bool = False,
        deadline: float = 5.0,
    ) -> ConnectionOptions:
        return ConnectionOptions(
            target=f"{host}:{port}",
            ca_file=self.certs / f"{ca}.crt" if ca else None,
            cert_file=self.certs / f"{client}.crt" if client else None,
            key_file=self.certs / f"{client}.key" if client else None,
            plaintext=plaintext,
            deadline_seconds=deadline,
        )

    def channel(self, port: int, **kwargs: object) -> grpc.Channel:
        return open_channel(self.options(port, **kwargs))  # type: ignore[arg-type]


def start_server(settings: GrpcServerSettings) -> RunningServer:
    running = build_server(settings)
    running.server.start()
    return running


@pytest.fixture(scope="session")
def servers(certs_dir: Path) -> Iterator[Servers]:
    ports = Servers(plaintext=free_port(), tls=free_port(), mtls=free_port(), certs=certs_dir)
    settings = GrpcServerSettings(
        bind_host="localhost",
        plaintext_port=ports.plaintext,
        tls_port=ports.tls,
        mtls_port=ports.mtls,
        server_cert_file=certs_dir / "server.crt",
        server_key_file=certs_dir / "server.key",
        client_ca_file=certs_dir / "ca.crt",
        max_message_bytes=16 * 1024,
    )
    running = start_server(settings)
    yield ports
    running.stop(grace=0)


@pytest.fixture(scope="session")
def expired_server(certs_dir: Path) -> Iterator[int]:
    port = free_port()
    settings = GrpcServerSettings(
        tls_port=port,
        mtls_port=0,
        server_cert_file=certs_dir / "expired-server.crt",
        server_key_file=certs_dir / "expired-server.key",
        client_ca_file=certs_dir / "ca.crt",
    )
    running = start_server(settings)
    yield port
    running.stop(grace=0)
