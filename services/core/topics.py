"""The workshop topic directory behind ListTopics/GetTopic and GET /v1/topics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from core.errors import NotFound


class Layer(StrEnum):
    APPLICATION = "application"
    SECURITY = "security"
    TRANSPORT = "transport"
    SERIALIZATION = "serialization"


@dataclass(frozen=True, slots=True)
class Topic:
    id: str
    title: str
    summary: str
    layer: Layer
    minutes: int


TOPICS: tuple[Topic, ...] = (
    Topic(
        "http",
        "How HTTP works",
        "Requests, responses, methods, headers and status codes.",
        Layer.APPLICATION,
        15,
    ),
    Topic(
        "tls",
        "HTTPS and TLS",
        "Encryption in transit, certificates and chains of trust.",
        Layer.SECURITY,
        20,
    ),
    Topic(
        "http2",
        "HTTP/2",
        "Binary framing, streams and multiplexing over one connection.",
        Layer.TRANSPORT,
        15,
    ),
    Topic(
        "protobuf",
        "Protocol Buffers",
        "A typed contract and a compact binary encoding.",
        Layer.SERIALIZATION,
        15,
    ),
    Topic(
        "grpc",
        "gRPC",
        "Remote procedure calls over HTTP/2 with Protocol Buffers.",
        Layer.APPLICATION,
        20,
    ),
    Topic(
        "streaming",
        "Streaming RPCs",
        "Server, client and bidirectional streams.",
        Layer.APPLICATION,
        20,
    ),
    Topic(
        "mtls",
        "Mutual TLS",
        "Both sides prove their identity with certificates.",
        Layer.SECURITY,
        20,
    ),
)
_BY_ID = {topic.id: topic for topic in TOPICS}


def list_topics(layer: Layer | None = None) -> list[Topic]:
    return [t for t in TOPICS if layer is None or t.layer == layer]


def get_topic(topic_id: str) -> Topic:
    topic = _BY_ID.get(topic_id.strip().lower())
    if topic is None:
        raise NotFound(f"topic {topic_id!r} does not exist")
    return topic
