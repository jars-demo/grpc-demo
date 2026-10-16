"""Open a TLS connection to a server and show what was negotiated: protocol version, cipher suite,
ALPN protocol (h2 for gRPC, http/1.1 for the REST API), and the certificate the server presented.

    uv run python examples/tls_inspect.py localhost 50051          # gRPC over TLS
    uv run python examples/tls_inspect.py localhost 8443           # REST over HTTPS
    uv run python examples/tls_inspect.py 127.0.0.1 50051          # hostname mismatch
    uv run python examples/tls_inspect.py localhost 50053          # expired certificate (Docker)

Uses Python's ssl module with full verification against --ca (default certs/out/ca.crt). It only
performs the handshake; it sends no HTTP request.
"""

from __future__ import annotations

import argparse
import socket
import ssl
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a TLS handshake")
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    parser.add_argument("--ca", type=Path, default=Path("certs/out/ca.crt"))
    args = parser.parse_args()

    context = ssl.create_default_context(cafile=str(args.ca))  # verifies chain AND hostname
    context.set_alpn_protocols(["h2", "http/1.1"])  # offer both; the server picks
    try:
        with (
            socket.create_connection((args.host, args.port), timeout=5) as raw,
            context.wrap_socket(raw, server_hostname=args.host) as tls,
        ):
            cert = tls.getpeercert()
            print(f"connected to {args.host}:{args.port}")
            print(f"  TLS version:  {tls.version()}")
            print(f"  cipher suite: {tls.cipher()[0] if tls.cipher() else '?'}")
            print(f"  ALPN:         {tls.selected_alpn_protocol() or '(none negotiated)'}")
            subject = dict(item[0] for item in cert["subject"])
            issuer = dict(item[0] for item in cert["issuer"])
            print(f"  subject CN:   {subject.get('commonName')}")
            print(f"  issuer CN:    {issuer.get('commonName')}")
            print(f"  serial:       {cert['serialNumber']}")
            print(f"  valid:        {cert['notBefore']}  ->  {cert['notAfter']}")
            print(f"  SAN:          {', '.join(v for _, v in cert.get('subjectAltName', ()))}")
    except ssl.SSLCertVerificationError as exc:
        print(
            f"certificate verification failed: {exc.verify_message} (code {exc.verify_code})",
            file=sys.stderr,
        )
        return 1
    except ssl.SSLError as exc:
        print(f"TLS handshake failed: {exc.reason}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"connection failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
