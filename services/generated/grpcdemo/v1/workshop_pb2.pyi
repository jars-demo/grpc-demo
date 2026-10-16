import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Layer(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LAYER_UNSPECIFIED: _ClassVar[Layer]
    LAYER_APPLICATION: _ClassVar[Layer]
    LAYER_SECURITY: _ClassVar[Layer]
    LAYER_TRANSPORT: _ClassVar[Layer]
    LAYER_SERIALIZATION: _ClassVar[Layer]
LAYER_UNSPECIFIED: Layer
LAYER_APPLICATION: Layer
LAYER_SECURITY: Layer
LAYER_TRANSPORT: Layer
LAYER_SERIALIZATION: Layer

class HelloRequest(_message.Message):
    __slots__ = ("name", "language", "simulated_delay_ms")
    NAME_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    SIMULATED_DELAY_MS_FIELD_NUMBER: _ClassVar[int]
    name: str
    language: str
    simulated_delay_ms: int
    def __init__(self, name: _Optional[str] = ..., language: _Optional[str] = ..., simulated_delay_ms: _Optional[int] = ...) -> None: ...

class HelloReply(_message.Message):
    __slots__ = ("message", "served_at", "transport_security", "client_identity")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SERVED_AT_FIELD_NUMBER: _ClassVar[int]
    TRANSPORT_SECURITY_FIELD_NUMBER: _ClassVar[int]
    CLIENT_IDENTITY_FIELD_NUMBER: _ClassVar[int]
    message: str
    served_at: _timestamp_pb2.Timestamp
    transport_security: str
    client_identity: str
    def __init__(self, message: _Optional[str] = ..., served_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., transport_security: _Optional[str] = ..., client_identity: _Optional[str] = ...) -> None: ...

class Topic(_message.Message):
    __slots__ = ("id", "title", "summary", "layer", "minutes")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    LAYER_FIELD_NUMBER: _ClassVar[int]
    MINUTES_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    summary: str
    layer: Layer
    minutes: int
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., summary: _Optional[str] = ..., layer: _Optional[_Union[Layer, str]] = ..., minutes: _Optional[int] = ...) -> None: ...

class ListTopicsRequest(_message.Message):
    __slots__ = ("layer",)
    LAYER_FIELD_NUMBER: _ClassVar[int]
    layer: Layer
    def __init__(self, layer: _Optional[_Union[Layer, str]] = ...) -> None: ...

class ListTopicsResponse(_message.Message):
    __slots__ = ("topics",)
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    topics: _containers.RepeatedCompositeFieldContainer[Topic]
    def __init__(self, topics: _Optional[_Iterable[_Union[Topic, _Mapping]]] = ...) -> None: ...

class GetTopicRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class WatchEventsRequest(_message.Message):
    __slots__ = ("count", "interval_ms")
    COUNT_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    count: int
    interval_ms: int
    def __init__(self, count: _Optional[int] = ..., interval_ms: _Optional[int] = ...) -> None: ...

class WorkshopEvent(_message.Message):
    __slots__ = ("sequence", "topic_id", "message", "emitted_at")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    TOPIC_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    EMITTED_AT_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    topic_id: str
    message: str
    emitted_at: _timestamp_pb2.Timestamp
    def __init__(self, sequence: _Optional[int] = ..., topic_id: _Optional[str] = ..., message: _Optional[str] = ..., emitted_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class Measurement(_message.Message):
    __slots__ = ("label", "value_ms")
    LABEL_FIELD_NUMBER: _ClassVar[int]
    VALUE_MS_FIELD_NUMBER: _ClassVar[int]
    label: str
    value_ms: float
    def __init__(self, label: _Optional[str] = ..., value_ms: _Optional[float] = ...) -> None: ...

class MeasurementSummary(_message.Message):
    __slots__ = ("count", "min_ms", "max_ms", "mean_ms", "p50_ms", "labels")
    COUNT_FIELD_NUMBER: _ClassVar[int]
    MIN_MS_FIELD_NUMBER: _ClassVar[int]
    MAX_MS_FIELD_NUMBER: _ClassVar[int]
    MEAN_MS_FIELD_NUMBER: _ClassVar[int]
    P50_MS_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    p50_ms: float
    labels: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, count: _Optional[int] = ..., min_ms: _Optional[float] = ..., max_ms: _Optional[float] = ..., mean_ms: _Optional[float] = ..., p50_ms: _Optional[float] = ..., labels: _Optional[_Iterable[str]] = ...) -> None: ...

class ChatMessage(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: _Optional[str] = ...) -> None: ...

class ChatReply(_message.Message):
    __slots__ = ("sequence", "echo", "reversed", "word_count", "received_at")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    ECHO_FIELD_NUMBER: _ClassVar[int]
    REVERSED_FIELD_NUMBER: _ClassVar[int]
    WORD_COUNT_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    echo: str
    reversed: str
    word_count: int
    received_at: _timestamp_pb2.Timestamp
    def __init__(self, sequence: _Optional[int] = ..., echo: _Optional[str] = ..., reversed: _Optional[str] = ..., word_count: _Optional[int] = ..., received_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetServerStatsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ServerStats(_message.Message):
    __slots__ = ("uptime_seconds", "calls_by_method", "caller_identity")
    class CallsByMethodEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    UPTIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    CALLS_BY_METHOD_FIELD_NUMBER: _ClassVar[int]
    CALLER_IDENTITY_FIELD_NUMBER: _ClassVar[int]
    uptime_seconds: float
    calls_by_method: _containers.ScalarMap[str, int]
    caller_identity: str
    def __init__(self, uptime_seconds: _Optional[float] = ..., calls_by_method: _Optional[_Mapping[str, int]] = ..., caller_identity: _Optional[str] = ...) -> None: ...
