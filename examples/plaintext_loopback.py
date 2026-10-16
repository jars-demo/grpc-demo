"""Chapter 05: a complete plaintext gRPC round trip on loopback, in one process.

    uv run python examples/plaintext_loopback.py
    docker compose --profile tools run --rm toolbox python examples/plaintext_loopback.py

Starts the real WorkshopService on 127.0.0.1 (a random free port, no TLS), calls SayHello through
the generated stub, and shuts the server down. Plaintext is acceptable here only because the bytes
never leave this machine's loopback interface. Everything after chapter 07 uses TLS.
"""

from __future__ import annotations

import sys
from concurrent import futures

import grpc

from grpc_server.servicer import WorkshopServicer
from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    pb_grpc.add_WorkshopServiceServicer_to_server(WorkshopServicer(), server)
    port = server.add_insecure_port("127.0.0.1:0")  # 0 = let the OS pick a free port
    server.start()
    print(f"server: listening on 127.0.0.1:{port} (plaintext, loopback only)")
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = pb_grpc.WorkshopServiceStub(channel)
            request = pb.HelloRequest(name="loopback")
            print(f"client: SayHello({request.name=})")
            reply = stub.SayHello(request, timeout=5)
            print(f"client: reply.message={reply.message!r}")
            print(f"client: reply.transport_security={reply.transport_security!r}")
            print(
                f"client: request is {len(request.SerializeToString())} bytes on the wire as protobuf"
            )
    finally:
        server.stop(grace=1).wait()
        print("server: stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
