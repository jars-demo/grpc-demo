"""Run the REST API over HTTP, or over HTTPS when REST_TLS_CERT_FILE and REST_TLS_KEY_FILE are set.

    uv run python -m rest_api                         # http://127.0.0.1:8080
    uv run python -m rest_api --https                 # https://localhost:8443 with certs/out/server.*

uvicorn speaks HTTP/1.1 here (it has no HTTP/2 support), which is itself a useful contrast with gRPC.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import uvicorn

from common.config import ConfigError, load_rest_settings
from common.logs import configure
from common.tls import CertificateFileError, read_pem
from rest_api.app import create_app


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m rest_api", description="Workshop REST API")
    parser.add_argument(
        "--https", action="store_true", help="serve HTTPS on :8443 with certs/out/server.crt"
    )
    args = parser.parse_args()
    overrides: dict[str, Any] = {}
    if args.https:
        overrides = {
            "port": 8443,
            "tls_cert_file": Path("certs/out/server.crt"),
            "tls_key_file": Path("certs/out/server.key"),
        }
    try:
        settings = load_rest_settings(**overrides)
        if settings.tls_cert_file and settings.tls_key_file:
            # Fail early with a helpful message instead of an ssl stack trace.
            read_pem(settings.tls_cert_file, "REST TLS certificate")
            read_pem(settings.tls_key_file, "REST TLS private key")
    except (ConfigError, CertificateFileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    configure(settings.log_level)
    uvicorn.run(
        create_app(settings.max_body_bytes),
        host=settings.bind_host,
        port=settings.port,
        ssl_certfile=str(settings.tls_cert_file) if settings.tls_cert_file else None,
        ssl_keyfile=str(settings.tls_key_file) if settings.tls_key_file else None,
        server_header=False,
        timeout_graceful_shutdown=5,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
