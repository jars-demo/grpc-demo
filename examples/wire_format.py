"""The same data as protobuf and as JSON: bytes on the wire, side by side.

    uv run python examples/wire_format.py

Serialization only - nothing is sent anywhere. Note what protobuf does NOT do: it does not encrypt.
Anyone who can read the bytes can decode them; confidentiality comes from TLS.
"""

from __future__ import annotations

import json
import sys

from google.protobuf import json_format

from grpcdemo.v1 import workshop_pb2 as pb


def show(label: str, proto: pb.HelloRequest | pb.Topic) -> None:
    binary = proto.SerializeToString()
    as_json = json.dumps(json_format.MessageToDict(proto), separators=(",", ":")).encode()
    print(f"{label}")
    print(f"  protobuf {len(binary):>3} bytes: {binary.hex(' ')}")
    print(f"  JSON     {len(as_json):>3} bytes: {as_json.decode()}")
    print()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    show("HelloRequest(name='Ada')", pb.HelloRequest(name="Ada"))
    show("HelloRequest(name='Ada', language='fr')", pb.HelloRequest(name="Ada", language="fr"))
    show(
        "Topic(id='grpc', ...)",
        pb.Topic(
            id="grpc",
            title="gRPC",
            summary="Remote procedure calls over HTTP/2.",
            layer=pb.LAYER_APPLICATION,
            minutes=20,
        ),
    )
    # Decoding the first byte by hand: field number and wire type are packed into one tag byte.
    tag = pb.HelloRequest(name="Ada").SerializeToString()[0]
    print(
        f"first byte 0x{tag:02x}: field number {tag >> 3}, wire type {tag & 0b111} (2 = length-delimited)"
    )
    print(
        "Field names never appear in the protobuf bytes - only numbers. That is why renumbering a field breaks clients."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
