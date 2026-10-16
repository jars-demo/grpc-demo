"""The four interaction patterns, error mapping, deadlines and limits, against a real server on
loopback. Uses the TLS listener (the normal path) unless a test is about plaintext."""

from __future__ import annotations

import time

import grpc
import pytest

from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc
from tests.conftest import Servers


@pytest.fixture
def stub(servers: Servers) -> pb_grpc.WorkshopServiceStub:
    channel = servers.channel(servers.tls)
    yield pb_grpc.WorkshopServiceStub(channel)
    channel.close()


# --- Unary -----------------------------------------------------------------------------------


def test_say_hello_over_tls_reports_tls_and_no_identity(stub: pb_grpc.WorkshopServiceStub) -> None:
    reply = stub.SayHello(pb.HelloRequest(name="Ada", language="de"), timeout=5)

    assert reply.message == "Hallo, Ada!"
    assert reply.transport_security == "tls"
    assert reply.client_identity == ""


def test_say_hello_over_plaintext_loopback_reports_plaintext(servers: Servers) -> None:
    with servers.channel(servers.plaintext, plaintext=True) as channel:
        reply = pb_grpc.WorkshopServiceStub(channel).SayHello(
            pb.HelloRequest(name="Ada"), timeout=5
        )

    assert reply.transport_security == "plaintext"


def test_invalid_argument_maps_to_invalid_argument_status(
    stub: pb_grpc.WorkshopServiceStub,
) -> None:
    with pytest.raises(grpc.RpcError) as info:
        stub.SayHello(pb.HelloRequest(name=""), timeout=5)

    assert info.value.code() == grpc.StatusCode.INVALID_ARGUMENT


def test_unknown_topic_maps_to_not_found(stub: pb_grpc.WorkshopServiceStub) -> None:
    with pytest.raises(grpc.RpcError) as info:
        stub.GetTopic(pb.GetTopicRequest(id="nope"), timeout=5)

    assert info.value.code() == grpc.StatusCode.NOT_FOUND


def test_list_topics_filters_by_layer(stub: pb_grpc.WorkshopServiceStub) -> None:
    response = stub.ListTopics(pb.ListTopicsRequest(layer=pb.LAYER_TRANSPORT), timeout=5)

    assert [t.id for t in response.topics] == ["http2"]


def test_message_over_size_limit_is_resource_exhausted(stub: pb_grpc.WorkshopServiceStub) -> None:
    with pytest.raises(grpc.RpcError) as info:
        stub.SayHello(pb.HelloRequest(name="x" * 20_000), timeout=5)  # server limit: 16 KiB

    assert info.value.code() == grpc.StatusCode.RESOURCE_EXHAUSTED


# --- Deadlines -------------------------------------------------------------------------------


def test_deadline_shorter_than_server_work_fails_with_deadline_exceeded(
    stub: pb_grpc.WorkshopServiceStub,
) -> None:
    started = time.monotonic()
    with pytest.raises(grpc.RpcError) as info:
        stub.SayHello(pb.HelloRequest(name="Ada", simulated_delay_ms=2000), timeout=0.3)

    assert info.value.code() == grpc.StatusCode.DEADLINE_EXCEEDED
    assert time.monotonic() - started < 1.5  # the client did not wait for the server


def test_deadline_longer_than_server_work_succeeds(stub: pb_grpc.WorkshopServiceStub) -> None:
    reply = stub.SayHello(pb.HelloRequest(name="Ada", simulated_delay_ms=100), timeout=3)

    assert reply.message == "Hello, Ada!"


# --- Server streaming ------------------------------------------------------------------------


def test_watch_events_streams_requested_count_in_order(stub: pb_grpc.WorkshopServiceStub) -> None:
    events = list(stub.WatchEvents(pb.WatchEventsRequest(count=4, interval_ms=0), timeout=5))

    assert [e.sequence for e in events] == [1, 2, 3, 4]
    assert events[0].topic_id == "http"


def test_watch_events_arrive_incrementally_not_all_at_the_end(
    stub: pb_grpc.WorkshopServiceStub,
) -> None:
    stream = stub.WatchEvents(pb.WatchEventsRequest(count=3, interval_ms=400), timeout=5)
    started = time.monotonic()
    next(stream)
    first_at = time.monotonic() - started
    list(stream)
    total = time.monotonic() - started

    assert first_at < 0.3
    assert total >= 0.75


def test_watch_events_deadline_cuts_stream_after_partial_delivery(
    stub: pb_grpc.WorkshopServiceStub,
) -> None:
    received = []
    with pytest.raises(grpc.RpcError) as info:
        for event in stub.WatchEvents(
            pb.WatchEventsRequest(count=10, interval_ms=300), timeout=1.0
        ):
            received.append(event.sequence)

    assert info.value.code() == grpc.StatusCode.DEADLINE_EXCEEDED
    assert 1 <= len(received) < 10


def test_watch_events_can_be_cancelled_by_client(stub: pb_grpc.WorkshopServiceStub) -> None:
    stream = stub.WatchEvents(pb.WatchEventsRequest(count=10, interval_ms=200), timeout=5)
    next(stream)
    stream.cancel()

    with pytest.raises(grpc.RpcError) as info:
        list(stream)

    assert info.value.code() == grpc.StatusCode.CANCELLED


def test_watch_events_rejects_invalid_count(stub: pb_grpc.WorkshopServiceStub) -> None:
    with pytest.raises(grpc.RpcError) as info:
        list(stub.WatchEvents(pb.WatchEventsRequest(count=0), timeout=5))

    assert info.value.code() == grpc.StatusCode.INVALID_ARGUMENT


# --- Client streaming ------------------------------------------------------------------------


def test_record_measurements_summarizes_the_whole_stream(stub: pb_grpc.WorkshopServiceStub) -> None:
    samples = [pb.Measurement(label="a", value_ms=v) for v in (5.0, 1.0, 3.0)]

    summary = stub.RecordMeasurements(iter(samples), timeout=5)

    assert (summary.count, summary.min_ms, summary.max_ms, summary.p50_ms) == (3, 1.0, 5.0, 3.0)
    assert list(summary.labels) == ["a"]


def test_record_measurements_rejects_empty_stream(stub: pb_grpc.WorkshopServiceStub) -> None:
    with pytest.raises(grpc.RpcError) as info:
        stub.RecordMeasurements(iter([]), timeout=5)

    assert info.value.code() == grpc.StatusCode.INVALID_ARGUMENT


# --- Bidirectional streaming -----------------------------------------------------------------


def test_chat_replies_to_each_message_before_the_client_finishes(
    stub: pb_grpc.WorkshopServiceStub,
) -> None:
    replies_seen_before_second_send: list[int] = []
    replies = None

    def requests():  # type: ignore[no-untyped-def]
        yield pb.ChatMessage(text="first message")
        # Wait until the reply to the first message has arrived: proves the server answers while
        # the client's side of the stream is still open.
        deadline = time.monotonic() + 3
        while not received and time.monotonic() < deadline:
            time.sleep(0.01)
        replies_seen_before_second_send.append(len(received))
        yield pb.ChatMessage(text="second")

    received: list[pb.ChatReply] = []
    replies = stub.Chat(requests(), timeout=5)
    for reply in replies:
        received.append(reply)

    assert replies_seen_before_second_send == [1]
    assert [(r.sequence, r.echo, r.word_count) for r in received] == [
        (1, "first message", 2),
        (2, "second", 1),
    ]
    assert received[0].reversed == "egassem tsrif"
