"""Logic for the three streaming RPCs. Kept free of gRPC types so it is easy to test."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from core.errors import InvalidArgument
from core.topics import TOPICS

MAX_EVENTS = 50
MAX_INTERVAL_MS = 5000
MAX_MEASUREMENTS = 10_000
MAX_LABEL_LENGTH = 64
MAX_CHAT_TEXT = 1000


# --- Server streaming: WatchEvents -----------------------------------------------------------


def validate_watch(count: int, interval_ms: int) -> None:
    if not 1 <= count <= MAX_EVENTS:
        raise InvalidArgument(f"count must be between 1 and {MAX_EVENTS}")
    if not 0 <= interval_ms <= MAX_INTERVAL_MS:
        raise InvalidArgument(f"interval_ms must be between 0 and {MAX_INTERVAL_MS}")


def event_for(sequence: int) -> tuple[str, str]:
    """The topic id and message for the event at 1-based `sequence` (cycles through the topics)."""
    topic = TOPICS[(sequence - 1) % len(TOPICS)]
    return topic.id, f"Now covering: {topic.title}"


# --- Client streaming: RecordMeasurements ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class Summary:
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    p50_ms: float
    labels: list[str]


def summarize(samples: Iterable[tuple[str, float]]) -> Summary:
    """Summarize (label, value_ms) samples. Consumes the iterable as it arrives."""
    values: list[float] = []
    labels: set[str] = set()
    for label, value in samples:
        if len(values) >= MAX_MEASUREMENTS:
            raise InvalidArgument(f"at most {MAX_MEASUREMENTS} measurements per stream")
        if len(label) > MAX_LABEL_LENGTH:
            raise InvalidArgument(f"label must be at most {MAX_LABEL_LENGTH} characters")
        if not math.isfinite(value) or value < 0:
            raise InvalidArgument("value_ms must be a finite, non-negative number")
        values.append(value)
        if label:
            labels.add(label)
    if not values:
        raise InvalidArgument("send at least one measurement")
    ordered = sorted(values)
    # Nearest-rank median: the smallest value with at least half the samples at or below it.
    p50 = ordered[math.ceil(0.5 * len(ordered)) - 1]
    return Summary(
        count=len(values),
        min_ms=ordered[0],
        max_ms=ordered[-1],
        mean_ms=sum(values) / len(values),
        p50_ms=p50,
        labels=sorted(labels),
    )


# --- Bidirectional streaming: Chat -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChatResult:
    echo: str
    reversed: str
    word_count: int


def respond(text: str) -> ChatResult:
    if len(text) > MAX_CHAT_TEXT:
        raise InvalidArgument(f"text must be at most {MAX_CHAT_TEXT} characters")
    return ChatResult(echo=text, reversed=text[::-1], word_count=len(text.split()))
