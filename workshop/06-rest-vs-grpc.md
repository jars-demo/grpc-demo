# 06 · REST vs gRPC

> ⏱ 10 minutes · The same operation through both doors, and what is (and is not) comparable.

## Learning objectives

- Compare the REST and gRPC versions of the same operations: addressing, serialization, errors, contracts, tooling.
- Map HTTP status codes and gRPC status codes onto each other.
- Avoid the common claim that gRPC is simply "faster" or "better".

## Prerequisites

Chapters 01 and 05. The stack is running.

## Concept

| | REST (this repo: FastAPI) | gRPC |
| --- | --- | --- |
| Addressing | resources and verbs: `GET /v1/topics/{id}` | methods: `WorkshopService/GetTopic` |
| Payload | JSON text (self-describing) | protobuf binary (needs the schema to decode) |
| Contract | optional (OpenAPI, generated here from code) | required (`.proto`, code generated from it) |
| Transport here | HTTP/1.1 (uvicorn has no HTTP/2) | HTTP/2 |
| Errors | HTTP status + JSON error body | gRPC status + message in trailers |
| Streaming | not built in (SSE, WebSockets, chunking) | four call patterns built in |
| Browsers | native | needs gRPC-Web and a proxy |
| Debugging | `curl`, any browser | `grpc_client`, `grpcurl` with the `.proto`, special tooling |

Equivalent operations in this repository:

| gRPC | REST | Error mapping |
| --- | --- | --- |
| `SayHello` | `POST /v1/greetings` | `INVALID_ARGUMENT` ↔ `422` |
| `ListTopics` | `GET /v1/topics?layer=...` | |
| `GetTopic` | `GET /v1/topics/{id}` | `NOT_FOUND` ↔ `404` |
| `grpc.health.v1.Health/Check` | `GET /health` | |
| message too large: `RESOURCE_EXHAUSTED` | `413` | |

**What is not directly comparable:** the REST service here runs HTTP/1.1, so a latency difference mixes protocol version, serialization and framework. JSON over HTTP/2 exists; gRPC over HTTP/3 is being worked on. Performance depends on payload size, concurrency, connection reuse, network distance and implementation quality. Measure your own workload (chapter 12).

## Exercise

### 1. The same request, twice

```bash
uv run python examples/rest_client.py https://localhost:8443/v1/topics/mtls
uv run python -m grpc_client topic mtls
```

**Expected:** the same data - `Mutual TLS`, `Both sides prove their identity with certificates.` - once as JSON, once printed from a protobuf message.

### 2. The same error, twice

```bash
uv run python examples/rest_client.py https://localhost:8443/v1/greetings --name Ada --language xx
uv run python -m grpc_client hello --name Ada --language xx
```

**Expected:** REST answers `HTTP/1.1 422 Unprocessable Content` with `"code": "INVALID_ARGUMENT"`; gRPC answers `RPC failed: INVALID_ARGUMENT` with `unsupported language 'xx'; use one of: de, en, es, fr, hi`. Both come from the same `core.errors.InvalidArgument`, mapped in `services/rest_api/app.py` and `services/grpc_server/errors.py`.

### 3. Payload size

```bash
uv run python examples/wire_format.py
```

**Expected:** a `Topic` is 53 bytes as protobuf and 117 bytes as JSON. Note what the comparison leaves out: HTTP headers, compression (gzip shrinks JSON considerably), and the fact that JSON is readable without the schema.

### 4. Two ways to describe the API

- REST: <http://localhost:8080/openapi.json>, generated from the Python code.
- gRPC: `services/proto/grpcdemo/v1/workshop.proto`, from which the code is generated.

## What just happened

Both interfaces did the same work, called the same functions, and failed the same way. The differences are in how the request is addressed, encoded and described, and in which tools can talk to it. gRPC gives you a strict contract, generated clients and streaming; REST gives you universal tooling, browser support and human-readable payloads. Many systems use both: gRPC between services, REST (or gRPC-Web) at the edge.

## Common failure: comparing apples to oranges

Running a latency test once, on loopback, with a tiny payload, and concluding "gRPC is 2× faster". **Diagnose:** ask what differs besides the protocol: HTTP version, serialization library, framework, connection reuse, payload size. **Fix:** change one variable at a time and measure repeatedly; chapter 12 shows how.

## Knowledge check

1. Which REST status corresponds to gRPC `NOT_FOUND`? To `PERMISSION_DENIED`?
2. Why can a browser not call this gRPC server directly with `fetch()`?
3. Name one thing REST makes easier than gRPC.

<details>
<summary>Answers</summary>

1. `404`; `403`.
2. Browsers do not expose HTTP/2 framing and trailers to JavaScript. gRPC-Web, with a translating proxy, works around that.
3. Debugging with ubiquitous tools (`curl`, a browser), human-readable payloads, caching by HTTP intermediaries, browser support.

</details>

## Done when

You can name, for one operation, its gRPC method, REST path, and the error code each side returns for bad input.

Next: [07 · Streaming RPCs](07-grpc-streaming.md)
