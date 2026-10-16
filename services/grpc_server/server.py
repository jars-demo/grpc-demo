"""Build and run the gRPC server.

One server process can listen on several ports with different credentials. The same servicers
answer on all of them; only the transport security differs:

    plaintext  (GRPC_PLAINTEXT_PORT, loopback only, off by default)  no encryption
    TLS        (GRPC_TLS_PORT, default 50051)                         server proves its identity
    mutual TLS (GRPC_MTLS_PORT, default 50052)                        both sides prove identity
"""

from __future__ import annotations

import logging
import signal
import threading
from concurrent import futures
from dataclasses import dataclass, field
from types import FrameType

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from common.config import GrpcServerSettings
from common.tls import server_credentials
from grpc_server.admin import AdminServicer
from grpc_server.servicer import WorkshopServicer
from grpc_server.stats import CallStats, StatsInterceptor
from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc

log = logging.getLogger("grpc_server")

SERVICE_NAMES = (
    pb.DESCRIPTOR.services_by_name["WorkshopService"].full_name,
    pb.DESCRIPTOR.services_by_name["AdminService"].full_name,
)


@dataclass
class RunningServer:
    server: grpc.Server
    health: health.HealthServicer
    # Port bound per enabled listener: "plaintext", "tls", "mtls".
    ports: dict[str, int] = field(default_factory=dict)

    def stop(self, grace: float) -> None:
        """Graceful shutdown: report NOT_SERVING, refuse new calls, let in-flight calls finish."""
        self.health.enter_graceful_shutdown()
        self.server.stop(grace).wait()


def build_server(settings: GrpcServerSettings) -> RunningServer:
    stats = CallStats()
    options = [
        ("grpc.max_receive_message_length", settings.max_message_bytes),
        ("grpc.max_send_message_length", settings.max_message_bytes),
    ]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=settings.max_workers, thread_name_prefix="rpc"),
        interceptors=[StatsInterceptor(stats)],
        options=options,
        # Each streaming call holds a worker thread; beyond this, new calls get RESOURCE_EXHAUSTED
        # instead of queueing forever.
        maximum_concurrent_rpcs=settings.max_workers * 4,
    )
    pb_grpc.add_WorkshopServiceServicer_to_server(WorkshopServicer(), server)
    pb_grpc.add_AdminServiceServicer_to_server(
        AdminServicer(stats, settings.admin_identities), server
    )

    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    for name in ("", *SERVICE_NAMES):
        health_servicer.set(name, health_pb2.HealthCheckResponse.SERVING)

    running = RunningServer(server=server, health=health_servicer)
    host = settings.bind_host
    if settings.plaintext_port:
        running.ports["plaintext"] = server.add_insecure_port(f"{host}:{settings.plaintext_port}")
    if settings.tls_port:
        creds = server_credentials(settings.server_cert_file, settings.server_key_file)
        running.ports["tls"] = server.add_secure_port(f"{host}:{settings.tls_port}", creds)
    if settings.mtls_port:
        creds = server_credentials(
            settings.server_cert_file, settings.server_key_file, settings.client_ca_file
        )
        running.ports["mtls"] = server.add_secure_port(f"{host}:{settings.mtls_port}", creds)
    for name, port in running.ports.items():
        if port == 0:
            raise RuntimeError(f"could not bind the {name} listener on {host}; is the port in use?")
    return running


def serve(settings: GrpcServerSettings) -> None:
    running = build_server(settings)
    running.server.start()
    for name, port in running.ports.items():
        note = (
            "  (plaintext: loopback only, for the introductory exercise)"
            if name == "plaintext"
            else ""
        )
        log.info("listening: %-9s %s:%d%s", name, settings.bind_host, port, note)

    stopping = threading.Event()

    def _on_signal(signum: int, _frame: FrameType | None) -> None:
        log.info(
            "received %s, shutting down (grace %.1fs)",
            signal.Signals(signum).name,
            settings.shutdown_grace_seconds,
        )
        stopping.set()

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)
    # Event.wait with a timeout keeps the main thread responsive to signals on Windows too.
    while not stopping.wait(0.5):
        pass
    running.stop(settings.shutdown_grace_seconds)
    log.info("stopped")
