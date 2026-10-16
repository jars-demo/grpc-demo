"""A tiny TCP relay that prints what crosses the wire. Point a client at the tap instead of the server.

    uv run python examples/wire_tap.py --listen 50060 --forward localhost:50050   # plaintext gRPC
    uv run python examples/wire_tap.py --listen 50060 --forward localhost:50051   # gRPC over TLS
    uv run python examples/wire_tap.py --listen 8090 --forward localhost:8080     # REST over HTTP

Then, in another terminal, send the client to the tap's port, e.g.:

    uv run python -m grpc_client --plaintext --target localhost:50060 hello --name Ada

What it shows:
  * readable text in each chunk (HTTP/1.1 is text; protobuf strings appear as-is; TLS is noise
    except the server name in the ClientHello, which is NOT encrypted);
  * for plaintext HTTP/2 (gRPC without TLS), each frame: type, flags and stream id.

It only relays bytes; it never decrypts anything. Stop it with Ctrl+C.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import string
import sys
from collections import defaultdict

H2_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
FRAME_TYPES = {
    0x0: "DATA", 0x1: "HEADERS", 0x2: "PRIORITY", 0x3: "RST_STREAM", 0x4: "SETTINGS",
    0x5: "PUSH_PROMISE", 0x6: "PING", 0x7: "GOAWAY", 0x8: "WINDOW_UPDATE", 0x9: "CONTINUATION",
}  # fmt: skip
FLAG_NAMES = {0x1: "END_STREAM/ACK", 0x4: "END_HEADERS", 0x8: "PADDED", 0x20: "PRIORITY"}
PRINTABLE = set(string.printable.encode()) - set(b"\t\n\r\x0b\x0c")


def readable(chunk: bytes, limit: int = 160) -> str:
    """Printable ASCII kept, everything else shown as '.'; long runs of dots collapsed."""
    text = "".join(chr(b) if b in PRINTABLE else "." for b in chunk)
    while "....." in text:
        text = text.replace(".....", "…")
    return text[:limit] + ("…" if len(text) > limit else "")


class H2Decoder:
    """Splits one direction of a plaintext HTTP/2 connection into frames."""

    def __init__(self) -> None:
        self.buffer = b""
        self.preface_checked = False
        self.active = True

    def feed(self, chunk: bytes) -> list[str]:
        if not self.active:
            return []
        self.buffer += chunk
        lines = []
        if not self.preface_checked:
            if self.buffer.startswith(H2_PREFACE):
                lines.append("connection preface: PRI * HTTP/2.0 (client says: I speak HTTP/2)")
                self.buffer = self.buffer[len(H2_PREFACE) :]
            elif len(self.buffer) >= 9 and self.buffer[3] == 0x4:
                pass  # server side starts directly with SETTINGS
            elif len(self.buffer) >= len(H2_PREFACE) or not H2_PREFACE.startswith(self.buffer[:24]):
                self.active = False  # not plaintext HTTP/2 (TLS or HTTP/1.1)
                return []
            else:
                return []
            self.preface_checked = True
        while len(self.buffer) >= 9:
            length = int.from_bytes(self.buffer[0:3], "big")
            if len(self.buffer) < 9 + length:
                break
            ftype, flags = self.buffer[3], self.buffer[4]
            stream = int.from_bytes(self.buffer[5:9], "big") & 0x7FFFFFFF
            payload = self.buffer[9 : 9 + length]
            self.buffer = self.buffer[9 + length :]
            names = [n for bit, n in FLAG_NAMES.items() if flags & bit]
            detail = ""
            if ftype == 0x0 and length >= 5:
                # gRPC message framing inside DATA: 1 byte compressed flag + 4 bytes length.
                detail = f"  gRPC message {int.from_bytes(payload[1:5], 'big')} bytes: {readable(payload[5:], 60)!r}"
            lines.append(
                f"frame {FRAME_TYPES.get(ftype, hex(ftype)):<13} stream={stream:<3} len={length:<5}"
                f" {'|'.join(names) or '-'}{detail}"
            )
        return lines


async def pipe(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, label: str, conn: int
) -> None:
    decoder = H2Decoder()
    try:
        while chunk := await reader.read(65536):
            print(f"[conn {conn}] {label} {len(chunk)} bytes | {readable(chunk)}")
            for line in decoder.feed(chunk):
                print(f"[conn {conn}]   {line}")
            writer.write(chunk)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()


async def main_async(listen: int, host: str, port: int) -> None:
    counter: defaultdict[str, int] = defaultdict(int)

    async def handle(client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter) -> None:
        counter["n"] += 1
        conn = counter["n"]
        print(f"[conn {conn}] client connected, relaying to {host}:{port}")
        try:
            server_r, server_w = await asyncio.open_connection(host, port)
        except OSError as exc:
            print(f"[conn {conn}] cannot reach {host}:{port}: {exc}")
            client_w.close()
            return
        await asyncio.gather(
            pipe(client_r, server_w, "client -> server", conn),
            pipe(server_r, client_w, "server -> client", conn),
        )
        print(f"[conn {conn}] closed")

    server = await asyncio.start_server(handle, "localhost", listen)
    print(f"wire tap listening on localhost:{listen}, forwarding to {host}:{port} (Ctrl+C to stop)")
    async with server:
        await server.serve_forever()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
    parser = argparse.ArgumentParser(description="Print the bytes between a client and a server")
    parser.add_argument("--listen", type=int, required=True, help="local port for clients")
    parser.add_argument("--forward", required=True, help="host:port of the real server")
    args = parser.parse_args()
    host, _, port = args.forward.rpartition(":")
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main_async(args.listen, host, int(port)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
