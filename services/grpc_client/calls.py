"""One function per RPC. Each takes an open channel and returns lines to print.

Every call passes `timeout=`: in gRPC that is the deadline, sent to the server in the
`grpc-timeout` header so both sides know when to give up.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Iterator

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from grpc_health.v1 import health_pb2, health_pb2_grpc

from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc


def _stub(channel: grpc.Channel) -> pb_grpc.WorkshopServiceStub:
    return pb_grpc.WorkshopServiceStub(channel)


def _time(ts: Timestamp) -> str:
    return ts.ToDatetime().strftime("%H:%M:%S.%f")[:-3]


def hello(
    channel: grpc.Channel, deadline: float, name: str, language: str = "", delay_ms: int = 0
) -> list[str]:
    request = pb.HelloRequest(name=name, language=language, simulated_delay_ms=delay_ms)
    reply, call = _stub(channel).SayHello.with_call(request, timeout=deadline)
    lines = [
        reply.message,
        f"  transport security: {reply.transport_security}",
    ]
    if reply.client_identity:
        lines.append(f"  client identity:    {reply.client_identity}")
    lines.append(f"  served at:          {_time(reply.served_at)} UTC")
    lines.append(f"  status:             {call.code().name}")
    return lines


def topics(channel: grpc.Channel, deadline: float, layer: str = "") -> list[str]:
    # Protobuf accepts an enum value by its name.
    layer_value = f"LAYER_{layer.upper()}" if layer else "LAYER_UNSPECIFIED"
    response = _stub(channel).ListTopics(pb.ListTopicsRequest(layer=layer_value), timeout=deadline)
    return [
        f"{t.id:<10} {pb.Layer.Name(t.layer).removeprefix('LAYER_').lower():<14} {t.minutes:>3} min  {t.title}"
        for t in response.topics
    ]


def topic(channel: grpc.Channel, deadline: float, topic_id: str) -> list[str]:
    t = _stub(channel).GetTopic(pb.GetTopicRequest(id=topic_id), timeout=deadline)
    return [
        f"{t.title} ({t.id})",
        f"  {t.summary}",
        f"  layer: {pb.Layer.Name(t.layer)}, {t.minutes} minutes",
    ]


def watch(channel: grpc.Channel, deadline: float, count: int, interval_ms: int) -> Iterator[str]:
    """Server streaming: print each event the moment it arrives."""
    started = time.monotonic()
    stream = _stub(channel).WatchEvents(
        pb.WatchEventsRequest(count=count, interval_ms=interval_ms), timeout=deadline
    )
    for event in stream:
        elapsed = time.monotonic() - started
        yield f"[{elapsed:6.2f}s] #{event.sequence:<2} {event.topic_id:<10} {event.message}"
    yield f"stream completed: {stream.code().name}"


def record(
    channel: grpc.Channel, deadline: float, samples: Iterable[tuple[str, float]]
) -> list[str]:
    """Client streaming: send every sample, then receive one summary."""
    requests = (pb.Measurement(label=label, value_ms=value) for label, value in samples)
    s = _stub(channel).RecordMeasurements(requests, timeout=deadline)
    return [
        f"count={s.count} min={s.min_ms:.2f}ms p50={s.p50_ms:.2f}ms mean={s.mean_ms:.2f}ms max={s.max_ms:.2f}ms",
        f"labels: {', '.join(s.labels) or '(none)'}",
    ]


def measure_hello(channel: grpc.Channel, deadline: float, calls: int) -> list[tuple[str, float]]:
    """Time `calls` sequential SayHello round trips on one channel (connection reused)."""
    stub = _stub(channel)
    samples = []
    for _ in range(calls):
        start = time.perf_counter()
        stub.SayHello(pb.HelloRequest(name="latency"), timeout=deadline)
        samples.append(("say-hello", (time.perf_counter() - start) * 1000))
    return samples


def chat(
    channel: grpc.Channel, deadline: float, messages: Iterable[str], pause_ms: int = 0
) -> Iterator[str]:
    """Bidirectional streaming. gRPC consumes the request iterator on its own thread, so messages
    go out while replies are printed as they arrive: you can watch the two directions interleave.
    `messages` may be a list or a live source such as stdin."""
    started = time.monotonic()

    def requests() -> Iterator[pb.ChatMessage]:
        for text in messages:
            if pause_ms:
                time.sleep(pause_ms / 1000)
            yield pb.ChatMessage(text=text.rstrip("\r\n"))

    replies = _stub(channel).Chat(requests(), timeout=deadline)
    for reply in replies:
        elapsed = time.monotonic() - started
        yield f"[{elapsed:6.2f}s] #{reply.sequence} {reply.echo!r} -> reversed {reply.reversed!r} ({reply.word_count} words)"
    yield f"stream completed: {replies.code().name}"


def stats(channel: grpc.Channel, deadline: float) -> list[str]:
    s = pb_grpc.AdminServiceStub(channel).GetServerStats(
        pb.GetServerStatsRequest(), timeout=deadline
    )
    lines = [f"caller: {s.caller_identity}", f"uptime: {s.uptime_seconds:.0f}s", "calls by method:"]
    lines += [f"  {count:>6}  {method}" for method, count in sorted(s.calls_by_method.items())]
    return lines


def health(channel: grpc.Channel, deadline: float, service: str = "") -> list[str]:
    reply = health_pb2_grpc.HealthStub(channel).Check(
        health_pb2.HealthCheckRequest(service=service), timeout=deadline
    )
    return [health_pb2.HealthCheckResponse.ServingStatus.Name(reply.status)]
