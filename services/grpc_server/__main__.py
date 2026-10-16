"""Run the gRPC server.

    uv run python -m grpc_server                 # TLS :50051 and mTLS :50052 (settings from env)
    uv run python -m grpc_server --plaintext     # also plaintext on localhost:50050 (chapter 05)
    uv run python -m grpc_server --plaintext-only

Needs `services` and `services/generated` on PYTHONPATH; the tasks script and Docker image set it.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from common.config import ConfigError, load_grpc_server_settings
from common.logs import configure
from common.tls import CertificateFileError
from grpc_server.server import serve

PLAINTEXT_PORT = 50050


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m grpc_server", description="Workshop gRPC server"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--plaintext",
        action="store_true",
        help=f"also listen without TLS on :{PLAINTEXT_PORT} (loopback only)",
    )
    mode.add_argument(
        "--plaintext-only",
        action="store_true",
        help="only the plaintext listener (no certificates needed)",
    )
    args = parser.parse_args()

    overrides: dict[str, Any] = {}
    if args.plaintext or args.plaintext_only:
        overrides["plaintext_port"] = PLAINTEXT_PORT
    if args.plaintext_only:
        overrides.update(tls_port=0, mtls_port=0)
    try:
        settings = load_grpc_server_settings(**overrides)
        configure(settings.log_level)
        serve(settings)
    except (ConfigError, CertificateFileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
