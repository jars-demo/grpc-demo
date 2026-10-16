"""Container health check: call the standard gRPC Health service over the real TLS listener.

    python -m grpc_server.healthcheck

This exercises the full path a client uses (TCP, TLS handshake with verification, HTTP/2, the
Health RPC), not just "is the process alive". Exits 0 when SERVING.
"""

from __future__ import annotations

import sys

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

from common.config import load_grpc_server_settings
from common.tls import channel_credentials


def main() -> int:
    settings = load_grpc_server_settings()
    host = "localhost"  # in the server certificate's SAN, and always local to the server
    try:
        if settings.tls_port:
            creds = channel_credentials(settings.client_ca_file)
            channel = grpc.secure_channel(f"{host}:{settings.tls_port}", creds)
        else:
            channel = grpc.insecure_channel(f"{host}:{settings.plaintext_port}")
        with channel:
            reply = health_pb2_grpc.HealthStub(channel).Check(
                health_pb2.HealthCheckRequest(), timeout=2
            )
    except grpc.RpcError as exc:
        print(f"unhealthy: {exc.code().name}: {exc.details()}", file=sys.stderr)
        return 1
    status = health_pb2.HealthCheckResponse.ServingStatus.Name(reply.status)
    print(status)
    return 0 if reply.status == health_pb2.HealthCheckResponse.SERVING else 1


if __name__ == "__main__":
    sys.exit(main())
