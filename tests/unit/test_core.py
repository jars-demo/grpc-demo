from __future__ import annotations

import math

import pytest

from core import greetings, streams, topics
from core.errors import InvalidArgument, NotFound


def test_greet_defaults_to_english() -> None:
    assert greetings.greet("Ada") == "Hello, Ada!"


def test_greet_uses_requested_language_case_insensitively() -> None:
    assert greetings.greet("Ada", "FR") == "Bonjour, Ada !"


def test_greet_trims_surrounding_whitespace() -> None:
    assert greetings.greet("  Ada  ") == "Hello, Ada!"


@pytest.mark.parametrize("name", ["", "   "])
def test_greet_rejects_empty_name(name: str) -> None:
    with pytest.raises(InvalidArgument, match="empty"):
        greetings.greet(name)


def test_greet_accepts_name_at_length_limit() -> None:
    assert greetings.greet("a" * 64) == f"Hello, {'a' * 64}!"


def test_greet_rejects_name_over_length_limit() -> None:
    with pytest.raises(InvalidArgument, match="at most 64"):
        greetings.greet("a" * 65)


def test_greet_rejects_control_characters() -> None:
    with pytest.raises(InvalidArgument, match="control"):
        greetings.greet("Ada\nX-Injected: 1")


def test_greet_rejects_unknown_language_and_lists_supported_ones() -> None:
    with pytest.raises(InvalidArgument, match="de, en, es, fr, hi"):
        greetings.greet("Ada", "xx")


@pytest.mark.parametrize("delay", [-1, 5001])
def test_validate_delay_rejects_out_of_range(delay: int) -> None:
    with pytest.raises(InvalidArgument):
        greetings.validate_delay_ms(delay)


def test_list_topics_filters_by_layer() -> None:
    assert [t.id for t in topics.list_topics(topics.Layer.SECURITY)] == ["tls", "mtls"]


def test_list_topics_without_filter_returns_all() -> None:
    assert len(topics.list_topics()) == len(topics.TOPICS)


def test_get_topic_is_case_insensitive() -> None:
    assert topics.get_topic(" GRPC ").id == "grpc"


def test_get_topic_raises_not_found_for_unknown_id() -> None:
    with pytest.raises(NotFound):
        topics.get_topic("nope")


@pytest.mark.parametrize(("count", "interval"), [(0, 0), (51, 0), (1, 5001)])
def test_validate_watch_rejects_out_of_range(count: int, interval: int) -> None:
    with pytest.raises(InvalidArgument):
        streams.validate_watch(count, interval)


def test_event_for_cycles_through_topics() -> None:
    first = streams.event_for(1)
    assert streams.event_for(len(topics.TOPICS) + 1) == first


def test_summarize_computes_statistics_and_sorted_distinct_labels() -> None:
    summary = streams.summarize([("b", 10.0), ("a", 30.0), ("b", 20.0), ("", 40.0)])

    assert (summary.count, summary.min_ms, summary.max_ms, summary.mean_ms) == (4, 10.0, 40.0, 25.0)
    assert summary.p50_ms == 20.0  # nearest rank: ceil(0.5 * 4) = 2nd smallest
    assert summary.labels == ["a", "b"]


def test_summarize_rejects_empty_stream() -> None:
    with pytest.raises(InvalidArgument, match="at least one"):
        streams.summarize([])


@pytest.mark.parametrize("value", [-0.1, math.inf, math.nan])
def test_summarize_rejects_invalid_values(value: float) -> None:
    with pytest.raises(InvalidArgument):
        streams.summarize([("x", value)])


def test_respond_reverses_and_counts_words() -> None:
    result = streams.respond("hello grpc world")
    assert (result.reversed, result.word_count) == ("dlrow cprg olleh", 3)


def test_respond_rejects_oversized_text() -> None:
    with pytest.raises(InvalidArgument):
        streams.respond("x" * 1001)
