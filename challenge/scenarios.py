"""Scenario definitions. The broken connection profiles live in challenge/scenarios/*.toml.

Each scenario runs a fixed client command against the real Docker stack with the learner's copy of
a profile (challenge/work/NN.toml). Only the profile may be changed: the servers, certificates and
command stay the same, as they would for a client team fixing its own configuration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    number: str
    slug: str
    title: str
    ticket: str
    command: tuple[str, ...]
    expected_mode: str  # the mode a correct fix uses: "tls" or "mtls"
    max_deadline: float | None
    hints: tuple[str, str, str]


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "01",
        "trust",
        "The certificate nobody trusts",
        "A client that worked yesterday now fails to connect to the TLS endpoint.",
        ("hello", "--name", "challenge-01"),
        "tls",
        None,
        (
            "Read the detail text: which step of the handshake failed - TCP, chain building, or hostname?",
            "Compare the issuer of the server certificate (certs.py inspect server) with the CA the profile trusts (openssl x509 -in <ca file> -noout -subject).",
            "The profile trusts a CA that did not issue the server certificate.",
        ),
    ),
    Scenario(
        "02",
        "hostname",
        "Right server, wrong name",
        "Someone 'optimized' the target to an IP address to skip DNS. Now TLS fails.",
        ("hello", "--name", "challenge-02"),
        "tls",
        None,
        (
            "The CA is right this time. Which other check does a TLS client perform on the server certificate?",
            "List the names the certificate is valid for: certs.py inspect server, look at Subject Alternative Name.",
            "The client checks the host in the target against the SAN list. An IP must appear as an IP SAN entry to match.",
        ),
    ),
    Scenario(
        "03",
        "missing-client-cert",
        "The door that asks for ID",
        "A new service connects to the mutual TLS port and is disconnected immediately.",
        ("hello", "--name", "challenge-03"),
        "mtls",
        None,
        (
            "The client sees only 'End of TCP stream'. The other side knows more: check the server log (docker compose logs grpc-server).",
            "PEER_DID_NOT_RETURN_A_CERTIFICATE: the server requires something the client did not send.",
            "Port 50052 requires a client certificate signed by the workshop CA. The profile has no cert/key.",
        ),
    ),
    Scenario(
        "04",
        "untrusted-client-cert",
        "Same name, wrong signature",
        "The client presents a certificate with the right name, but the server still hangs up.",
        ("hello", "--name", "challenge-04"),
        "mtls",
        None,
        (
            "Server log again. This time the client did send a certificate. What did the server think of it?",
            "Inspect the client certificate's issuer: certs.py inspect rogue-client vs certs.py inspect client.",
            "A certificate is only as good as its issuer. The server trusts certificates from the workshop CA only.",
        ),
    ),
    Scenario(
        "05",
        "authorization",
        "Authenticated is not authorized",
        "The mutual TLS handshake succeeds, but reading server stats is refused.",
        ("stats",),
        "mtls",
        None,
        (
            "The status is not UNAVAILABLE: the connection worked. What does this status code mean?",
            "PERMISSION_DENIED means the server knows who you are and has decided you may not do this.",
            "AdminService authorizes by the certificate's Common Name. Which workshop certificate carries the admin identity?",
        ),
    ),
    Scenario(
        "06",
        "deadline",
        "Impatient client",
        "A known-slow call (about 0.8 s) fails every time, but the server is healthy.",
        ("hello", "--name", "challenge-06", "--delay-ms", "800"),
        "tls",
        5.0,
        (
            "Which status code do you get, and who decided to give up: client or server?",
            "The deadline is part of the client's configuration. How long does this call need?",
            "Raise deadline_seconds above the call's duration, with headroom, but keep it bounded (at most 5 s here).",
        ),
    ),
)
BY_NUMBER = {s.number: s for s in SCENARIOS}
