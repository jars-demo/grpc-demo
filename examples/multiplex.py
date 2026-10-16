"""Chapter 03: several RPCs at once over ONE HTTP/2 connection.

    uv run python examples/multiplex.py --plaintext --target localhost:50060   # through the wire tap
    uv run python examples/multiplex.py                                         # TLS, localhost:50051

Starts three WatchEvents streams concurrently on a single channel. With HTTP/1.1 each concurrent
request needs its own TCP connection; HTTP/2 gives each call its own stream id (1, 3, 5, ...) and
interleaves their frames on one connection. Watch the wire tap: one "client connected" line, three
stream ids.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import grpc

from grpc_client.connection import ConnectionOptions, open_channel
from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", default="localhost:50051")
    parser.add_argument("--plaintext", action="store_true", help="loopback only")
    parser.add_argument("--ca", type=Path, default=Path("certs/out/ca.crt"))
    args = parser.parse_args()
    options = ConnectionOptions(target=args.target, ca_file=args.ca, plaintext=args.plaintext)

    started = time.monotonic()
    lock = threading.Lock()

    with open_channel(options) as channel:
        stub = pb_grpc.WorkshopServiceStub(channel)

        def watch(name: str, interval_ms: int) -> None:
            request = pb.WatchEventsRequest(count=3, interval_ms=interval_ms)
            try:
                for event in stub.WatchEvents(request, timeout=10):
                    with lock:
                        print(
                            f"[{time.monotonic() - started:5.2f}s] {name} event #{event.sequence} {event.topic_id}"
                        )
            except grpc.RpcError as exc:
                print(f"{name} failed: {exc.code().name}: {exc.details()}")

        threads = [threading.Thread(target=watch, args=(f"call-{i}", 150 * i)) for i in (1, 2, 3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    print(f"three calls, one channel, {time.monotonic() - started:.2f}s total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
