"""What happens when client and server disagree about the contract.

    uv run python examples/contract_mismatch.py                 # against localhost:50051 (TLS)

Calls a method that a newer, hypothetical version of the .proto (`grpcdemo.v2`) would have, but
the running server does not implement. gRPC routes by the path `/package.Service/Method`, so the
server answers UNIMPLEMENTED. Nothing is simulated: the request really goes to the server.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import grpc

from common.tls import channel_credentials
from grpcdemo.v1 import workshop_pb2 as pb

MISSING_METHOD = "/grpcdemo.v2.WorkshopService/SayHello"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", default="localhost:50051")
    parser.add_argument("--ca", type=Path, default=Path("certs/out/ca.crt"))
    args = parser.parse_args()
    with grpc.secure_channel(args.target, channel_credentials(args.ca)) as channel:
        call = channel.unary_unary(
            MISSING_METHOD,
            request_serializer=pb.HelloRequest.SerializeToString,
            response_deserializer=pb.HelloReply.FromString,
        )
        print(f"calling {MISSING_METHOD} on {args.target}")
        try:
            call(pb.HelloRequest(name="v2 client"), timeout=5)
        except grpc.RpcError as exc:
            print(f"status:  {exc.code().name}")
            print(f"details: {exc.details()}")
            return 0 if exc.code() == grpc.StatusCode.UNIMPLEMENTED else 1
    print("unexpected: the call succeeded")
    return 1


if __name__ == "__main__":
    sys.exit(main())
