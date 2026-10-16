"""AdminService: authentication (mutual TLS) is not authorization.

Any client holding a certificate from the workshop CA can complete the mTLS handshake. That proves
who the caller is. This servicer then decides what that identity may do: only identities listed
in GRPC_ADMIN_IDENTITIES may read server statistics.
"""

from __future__ import annotations

import logging

import grpc

from common.tls import client_identity
from grpc_server.stats import CallStats
from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc

log = logging.getLogger("grpc_server.authz")


def authorize(context: grpc.ServicerContext, allowed: frozenset[str]) -> str:
    """Return the caller's identity if it is allowed; abort the call otherwise."""
    identity = client_identity(context.auth_context())
    if not identity:
        # No verified client certificate on this connection (plaintext or server-only TLS).
        context.abort(
            grpc.StatusCode.UNAUTHENTICATED,
            "AdminService requires a client certificate: connect to the mutual TLS port",
        )
    if identity not in allowed:
        log.warning("denied identity=%s method=%s", identity, "GetServerStats")
        context.abort(
            grpc.StatusCode.PERMISSION_DENIED,
            f"identity {identity!r} is authenticated but not authorized for AdminService",
        )
    return identity


class AdminServicer(pb_grpc.AdminServiceServicer):
    def __init__(self, stats: CallStats, admin_identities: frozenset[str]) -> None:
        self._stats = stats
        self._admins = admin_identities

    def GetServerStats(
        self, request: pb.GetServerStatsRequest, context: grpc.ServicerContext
    ) -> pb.ServerStats:
        identity = authorize(context, self._admins)
        return pb.ServerStats(
            uptime_seconds=self._stats.uptime_seconds,
            calls_by_method=self._stats.snapshot(),
            caller_identity=identity,
        )
