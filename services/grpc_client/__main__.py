"""The workshop gRPC client.

    python -m grpc_client hello --name Ada                       # TLS to localhost:50051
    python -m grpc_client --plaintext --target localhost:50050 hello
    python -m grpc_client --target localhost:50052 --cert certs/out/client.crt --key certs/out/client.key hello
    python -m grpc_client --profile challenge/work/01.toml hello

Run `python -m grpc_client --help` and `python -m grpc_client <command> --help` for every option.
Exit codes: 0 success, 1 the RPC failed (explained on stderr), 2 bad configuration.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

import grpc

from common.config import ConfigError, load_client_settings
from common.tls import CertificateFileError
from grpc_client import calls
from grpc_client.connection import (
    ConnectionConfigError,
    ConnectionOptions,
    load_profile,
    open_channel,
)
from grpc_client.diagnose import diagnose


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m grpc_client", description="Workshop gRPC client")
    conn = p.add_argument_group("connection")
    conn.add_argument("--target", help="host:port (default: $GRPC_TARGET or localhost:50051)")
    trust = conn.add_mutually_exclusive_group()
    trust.add_argument(
        "--ca", type=Path, help="CA certificate to trust (default: certs/out/ca.crt)"
    )
    trust.add_argument(
        "--system-roots",
        action="store_true",
        help="trust gRPC's bundled public CAs instead of the workshop CA (chapter 09)",
    )
    conn.add_argument("--cert", type=Path, help="client certificate, for mutual TLS")
    conn.add_argument("--key", type=Path, help="client private key, for mutual TLS")
    conn.add_argument(
        "--plaintext", action="store_true", help="no TLS; loopback targets only (chapter 05)"
    )
    conn.add_argument(
        "--deadline", type=float, help="seconds before the call is abandoned (default 5)"
    )
    conn.add_argument("--profile", type=Path, help="TOML connection profile (final challenge)")
    conn.add_argument(
        "--show-connection", action="store_true", help="print the effective connection settings"
    )

    sub = p.add_subparsers(dest="command", required=True, metavar="command")
    h = sub.add_parser("hello", help="unary: SayHello")
    h.add_argument("--name", default="workshop")
    h.add_argument("--language", default="", help="en, es, fr, de, hi")
    h.add_argument(
        "--delay-ms", type=int, default=0, help="ask the server to wait (deadline exercises)"
    )

    t = sub.add_parser("topics", help="unary: ListTopics")
    t.add_argument(
        "--layer", default="", choices=["", "application", "security", "transport", "serialization"]
    )
    g = sub.add_parser("topic", help="unary: GetTopic")
    g.add_argument("id")

    w = sub.add_parser("watch", help="server streaming: WatchEvents")
    w.add_argument("--count", type=int, default=5)
    w.add_argument("--interval-ms", type=int, default=500)

    r = sub.add_parser("record", help="client streaming: RecordMeasurements")
    r.add_argument("values", nargs="*", type=float, help="latency samples in ms")
    r.add_argument("--label", default="manual")
    r.add_argument(
        "--measure-hello", type=int, metavar="N", help="time N real SayHello calls and send those"
    )

    c = sub.add_parser("chat", help="bidirectional streaming: Chat (reads stdin if no messages)")
    c.add_argument("messages", nargs="*")
    c.add_argument("--pause-ms", type=int, default=0, help="pause before each message is sent")

    sub.add_parser("stats", help="AdminService.GetServerStats (mTLS + authorization)")
    sub.add_parser("health", help="standard grpc.health.v1 check")
    return p


def resolve_options(args: argparse.Namespace) -> ConnectionOptions:
    settings = load_client_settings()
    options = ConnectionOptions(
        target=settings.target,
        ca_file=settings.ca_file,
        cert_file=settings.client_cert_file,
        key_file=settings.client_key_file,
        deadline_seconds=settings.deadline_seconds,
    )
    if args.profile:
        options = load_profile(args.profile, options)
    overrides = {
        "target": args.target,
        "ca_file": args.ca,
        "cert_file": args.cert,
        "key_file": args.key,
        "deadline_seconds": args.deadline,
    }
    values = {**options.__dict__, **{k: v for k, v in overrides.items() if v is not None}}
    if args.system_roots:
        values["ca_file"] = None
    if args.plaintext:
        values["plaintext"] = True
    return ConnectionOptions(**values)


def run_command(args: argparse.Namespace, channel: grpc.Channel, deadline: float) -> Iterable[str]:
    match args.command:
        case "hello":
            return calls.hello(channel, deadline, args.name, args.language, args.delay_ms)
        case "topics":
            return calls.topics(channel, deadline, args.layer)
        case "topic":
            return calls.topic(channel, deadline, args.id)
        case "watch":
            return calls.watch(channel, deadline, args.count, args.interval_ms)
        case "record":
            samples = [(args.label, v) for v in args.values]
            if args.measure_hello:
                samples += calls.measure_hello(channel, deadline, args.measure_hello)
            return calls.record(channel, deadline, samples)
        case "chat":
            return calls.chat(channel, deadline, args.messages or sys.stdin, args.pause_ms)
        case "stats":
            return calls.stats(channel, deadline)
        case "health":
            return calls.health(channel, deadline)
    raise AssertionError(args.command)


def main(argv: list[str] | None = None) -> int:
    # Greetings include non-Latin scripts; legacy Windows consoles default to cp1252.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        options = resolve_options(args)
        if args.show_connection:
            print(
                f"# {options.mode} -> {options.target}  ca={options.ca_file or '(gRPC bundled roots)'}  "
                f"cert={options.cert_file or '-'}  deadline={options.deadline_seconds}s",
                file=sys.stderr,
            )
        with open_channel(options) as channel:
            for line in run_command(args, channel, options.deadline_seconds):
                print(line, flush=True)
    except grpc.RpcError as exc:
        print(diagnose(exc).render(), file=sys.stderr)
        return 1
    except (ConfigError, ConnectionConfigError, CertificateFileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
