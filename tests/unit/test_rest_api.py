from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from rest_api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(max_body_bytes=1024))


def test_create_greeting_returns_message_and_scheme(client: TestClient) -> None:
    response = client.post("/v1/greetings", json={"name": "Ada", "language": "es"})

    assert response.status_code == 200
    assert response.json()["message"] == "¡Hola, Ada!"
    assert response.json()["transport_security"] == "http"


def test_create_greeting_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post("/v1/greetings", json={"name": "Ada", "admin": True})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ARGUMENT"


def test_create_greeting_rejects_empty_name_with_field_in_message(client: TestClient) -> None:
    response = client.post("/v1/greetings", json={"name": ""})

    assert response.status_code == 422
    assert response.json()["error"]["message"].startswith("name:")


def test_domain_validation_maps_to_422(client: TestClient) -> None:
    response = client.post("/v1/greetings", json={"name": "Ada", "language": "xx"})

    assert response.status_code == 422
    assert "unsupported language" in response.json()["error"]["message"]


def test_unknown_topic_returns_404_with_error_body(client: TestClient) -> None:
    response = client.get("/v1/topics/nope")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "topic 'nope' does not exist"}
    }


def test_list_topics_filters_by_layer(client: TestClient) -> None:
    response = client.get("/v1/topics", params={"layer": "transport"})

    assert [t["id"] for t in response.json()["topics"]] == ["http2"]


def test_list_topics_rejects_unknown_layer(client: TestClient) -> None:
    assert client.get("/v1/topics", params={"layer": "physical"}).status_code == 422


def test_body_over_limit_is_rejected_with_413(client: TestClient) -> None:
    response = client.post(
        "/v1/greetings", content=b"x" * 2048, headers={"content-type": "application/json"}
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_chunked_body_over_limit_is_rejected_with_413(client: TestClient) -> None:
    def chunks():  # type: ignore[no-untyped-def]
        for _ in range(4):
            yield b"x" * 512

    response = client.post(
        "/v1/greetings", content=chunks(), headers={"content-type": "application/json"}
    )

    assert response.status_code == 413


def test_responses_carry_security_headers(client: TestClient) -> None:
    response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert "server" not in response.headers


def test_openapi_documents_the_greeting_endpoint(client: TestClient) -> None:
    assert "/v1/greetings" in client.get("/openapi.json").json()["paths"]
