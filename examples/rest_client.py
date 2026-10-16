"""REST client: the HTTP side of the comparison, with strict certificate verification for HTTPS.

    uv run python examples/rest_client.py http://127.0.0.1:8080/v1/topics
    uv run python examples/rest_client.py https://localhost:8443/v1/topics/grpc
    uv run python examples/rest_client.py https://localhost:8443/v1/greetings --name Ada --language es
    uv run python examples/rest_client.py https://127.0.0.1:8443/health       # hostname mismatch

For https:// URLs the server certificate is verified against --ca (default certs/out/ca.crt):
the chain must lead to that CA and the URL's host must be in the certificate's SAN list.
There is no option to turn verification off.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="REST client for the workshop")
    parser.add_argument("url")
    parser.add_argument("--name", help="POST a greeting request with this name")
    parser.add_argument("--language", default="", help="greeting language (with --name)")
    parser.add_argument(
        "--delay-ms", type=int, default=0, help="ask the server to wait (with --name)"
    )
    parser.add_argument("--post", metavar="JSON", help="POST this raw JSON body (bash/zsh quoting)")
    parser.add_argument(
        "--ca", type=Path, default=Path("certs/out/ca.crt"), help="CA to trust for HTTPS"
    )
    parser.add_argument(
        "--timeout", type=float, default=5.0, help="seconds (the REST analogue of a deadline)"
    )
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    if args.url.startswith("https://") and not args.ca.exists():
        print(
            f"error: {args.ca} not found. Run: uv run python certs/scripts/certs.py generate",
            file=sys.stderr,
        )
        return 2
    # The default context verifies the chain (against --ca only) AND the hostname (against the SAN).
    verify = (
        ssl.create_default_context(cafile=str(args.ca)) if args.url.startswith("https://") else True
    )
    try:
        with httpx.Client(verify=verify, timeout=args.timeout) as client:
            if args.name is not None:
                body: dict[str, object] = {"name": args.name}
                if args.language:
                    body["language"] = args.language
                if args.delay_ms:
                    body["simulated_delay_ms"] = args.delay_ms
                response = client.post(args.url, json=body)
            elif args.post is not None:
                response = client.post(args.url, json=json.loads(args.post))
            else:
                response = client.get(args.url)
    except httpx.ConnectError as exc:
        print(f"connection failed: {exc}", file=sys.stderr)
        return 1
    except httpx.TimeoutException:
        print(f"timed out after {args.timeout}s", file=sys.stderr)
        return 1

    print(f"{response.http_version} {response.status_code} {response.reason_phrase}")
    for name in ("content-type", "content-length"):
        if name in response.headers:
            print(f"{name}: {response.headers[name]}")
    print()
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return 0 if response.is_success else 1


if __name__ == "__main__":
    sys.exit(main())
