"""WorkshopService: one method per gRPC interaction pattern.

Each method validates its input, calls the transport-independent logic in `core`, and converts the
result to protobuf messages. Long waits use `_Lifetime.wait`, which returns early when the client
cancels or its deadline expires, so the server stops working on calls nobody is waiting for.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from common.tls import client_identity, transport_security
from core import greetings, streams, topics
from grpc_server.errors import domain_errors
from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc

LAYER_TO_PROTO = {
    topics.Layer.APPLICATION: pb.LAYER_APPLICATION,
    topics.Layer.SECURITY: pb.LAYER_SECURITY,
    topics.Layer.TRANSPORT: pb.LAYER_TRANSPORT,
    topics.Layer.SERIALIZATION: pb.LAYER_SERIALIZATION,
}
PROTO_TO_LAYER = {v: k for k, v in LAYER_TO_PROTO.items()}


def _now() -> Timestamp:
    ts = Timestamp()
    ts.GetCurrentTime()
    return ts


def _topic(topic: topics.Topic) -> pb.Topic:
    return pb.Topic(
        id=topic.id,
        title=topic.title,
        summary=topic.summary,
        layer=LAYER_TO_PROTO[topic.layer],
        minutes=topic.minutes,
    )


class _Lifetime:
    """Signals when an RPC ends for any reason: completed, cancelled, or deadline exceeded."""

    def __init__(self, context: grpc.ServicerContext) -> None:
        self._done = threading.Event()
        context.add_callback(self._done.set)

    def wait(self, seconds: float) -> bool:
        """Sleep up to `seconds`. Returns False if the RPC ended meanwhile (stop working)."""
        return not self._done.wait(seconds)


class WorkshopServicer(pb_grpc.WorkshopServiceServicer):
    # --- Unary ---------------------------------------------------------------------------------

    def SayHello(self, request: pb.HelloRequest, context: grpc.ServicerContext) -> pb.HelloReply:
        with domain_errors(context):
            message = greetings.greet(request.name, request.language)
            delay_ms = greetings.validate_delay_ms(request.simulated_delay_ms)
        if delay_ms and not _Lifetime(context).wait(delay_ms / 1000):
            # The client gave up (deadline or cancel). Whatever we return now is discarded.
            return pb.HelloReply()
        auth = context.auth_context()
        return pb.HelloReply(
            message=message,
            served_at=_now(),
            transport_security=transport_security(auth),
            client_identity=client_identity(auth),
        )

    def ListTopics(
        self, request: pb.ListTopicsRequest, context: grpc.ServicerContext
    ) -> pb.ListTopicsResponse:
        layer = PROTO_TO_LAYER.get(request.layer)  # LAYER_UNSPECIFIED -> None -> all topics
        return pb.ListTopicsResponse(topics=[_topic(t) for t in topics.list_topics(layer)])

    def GetTopic(self, request: pb.GetTopicRequest, context: grpc.ServicerContext) -> pb.Topic:
        with domain_errors(context):
            return _topic(topics.get_topic(request.id))

    # --- Server streaming ----------------------------------------------------------------------

    def WatchEvents(
        self, request: pb.WatchEventsRequest, context: grpc.ServicerContext
    ) -> Iterator[pb.WorkshopEvent]:
        with domain_errors(context):
            streams.validate_watch(request.count, request.interval_ms)
        lifetime = _Lifetime(context)
        for sequence in range(1, request.count + 1):
            if sequence > 1 and not lifetime.wait(request.interval_ms / 1000):
                return  # client cancelled or deadline passed: stop producing events
            topic_id, message = streams.event_for(sequence)
            yield pb.WorkshopEvent(
                sequence=sequence, topic_id=topic_id, message=message, emitted_at=_now()
            )

    # --- Client streaming ----------------------------------------------------------------------

    def RecordMeasurements(
        self, request_iterator: Iterator[pb.Measurement], context: grpc.ServicerContext
    ) -> pb.MeasurementSummary:
        with domain_errors(context):
            summary = streams.summarize((m.label, m.value_ms) for m in request_iterator)
        return pb.MeasurementSummary(
            count=summary.count,
            min_ms=summary.min_ms,
            max_ms=summary.max_ms,
            mean_ms=summary.mean_ms,
            p50_ms=summary.p50_ms,
            labels=summary.labels,
        )

    # --- Bidirectional streaming ---------------------------------------------------------------

    def Chat(
        self, request_iterator: Iterator[pb.ChatMessage], context: grpc.ServicerContext
    ) -> Iterator[pb.ChatReply]:
        # Reply to each message as soon as it arrives; the loop ends when the client half-closes.
        for sequence, message in enumerate(request_iterator, start=1):
            with domain_errors(context):
                result = streams.respond(message.text)
            yield pb.ChatReply(
                sequence=sequence,
                echo=result.echo,
                reversed=result.reversed,
                word_count=result.word_count,
                received_at=_now(),
            )
