# 04 · Protocol Buffers

> ⏱ 15 minutes · A typed contract, a compact encoding, and generated code.

## Learning objectives

- Read a `.proto` file: packages, services, RPCs, messages, field numbers, enums.
- Generate Python bindings and know why generated code is never edited by hand.
- Explain why field *numbers*, not names, define the wire format - and what that means for compatibility.
- State clearly that Protocol Buffers are serialization, not encryption.

## Prerequisites

Chapter 00 (`uv sync` done).

## Concept

**Protocol Buffers** (protobuf) are two things:

1. an **interface definition language**: you describe messages and services in a `.proto` file;
2. a **binary serialization format**: messages are encoded as compact tag-length-value bytes.

The contract for this workshop is `services/proto/grpcdemo/v1/workshop.proto`. An excerpt:

```protobuf
service WorkshopService {
  rpc SayHello(HelloRequest) returns (HelloReply);
  rpc WatchEvents(WatchEventsRequest) returns (stream WorkshopEvent);
  rpc RecordMeasurements(stream Measurement) returns (MeasurementSummary);
  rpc Chat(stream ChatMessage) returns (stream ChatReply);
}

message HelloRequest {
  string name = 1;
  string language = 2;
  uint32 simulated_delay_ms = 3;
}
```

The `= 1`, `= 2`, `= 3` are **field numbers**. On the wire, a field is identified by its number and a wire type, never by its name. Consequences:

- Renaming a field is safe on the wire; **renumbering** one breaks every existing client.
- Adding a new field with a new number is backwards compatible: old readers skip unknown fields.
- A deleted field's number must never be reused - mark it `reserved`.
- In proto3, a field that is not set reads as its default (`""`, `0`, the first enum value), which is why enums start with an `..._UNSPECIFIED = 0` value.

The `grpc_tools.protoc` compiler turns the contract into code: message classes (`workshop_pb2.py`), type stubs (`.pyi`), and client stubs plus server base classes (`workshop_pb2_grpc.py`).

## Exercise

### 1. Regenerate the bindings and check they match

```bash
uv run python scripts/generate_proto.py
uv run python scripts/generate_proto.py --check
```

**Expected:**

```text
wrote services/generated/grpcdemo/v1/workshop_pb2.py
wrote services/generated/grpcdemo/v1/workshop_pb2.pyi
wrote services/generated/grpcdemo/v1/workshop_pb2_grpc.py
OK: 3 generated files match 1 .proto file(s)
```

CI runs `--check` on every change: if someone edits the `.proto` without regenerating, or edits generated code by hand, the build fails.

### 2. Look at the bytes

```bash
uv run python examples/wire_format.py
```

**Expected:**

```text
HelloRequest(name='Ada')
  protobuf   5 bytes: 0a 03 41 64 61
  JSON      14 bytes: {"name":"Ada"}

HelloRequest(name='Ada', language='fr')
  protobuf   9 bytes: 0a 03 41 64 61 12 02 66 72
  JSON      30 bytes: {"name":"Ada","language":"fr"}
...
first byte 0x0a: field number 1, wire type 2 (2 = length-delimited)
```

Decode `0a 03 41 64 61` yourself: `0a` = field 1, length-delimited; `03` = three bytes follow; `41 64 61` = ASCII `Ada`. Then `12 02 66 72`: field 2, two bytes, `fr`.

### 3. Change the contract (and put it back)

Open `workshop.proto` and change `string name = 1;` to `string name = 7;`. Regenerate and re-run the example:

```bash
uv run python scripts/generate_proto.py
uv run python examples/wire_format.py
```

**Expected:** the first message is now `3a 03 41 64 61` (`0x3a` = field 7, wire type 2). A server built from the old contract would read field 7 as an unknown field and see an *empty name*. Restore the line to `= 1`, regenerate, and confirm with `--check`:

```bash
uv run python scripts/generate_proto.py
uv run python scripts/generate_proto.py --check
```

## What just happened

The contract, not the code, is the source of truth. Both sides of a gRPC call are generated from the same `.proto`, so the compiler - not documentation - keeps client and server in agreement about message shapes. The encoding is small because it carries numbers instead of names; it is *not* secret. Anyone who can capture the bytes can decode them, exactly as you just did. Confidentiality comes from TLS.

## Common failure: `RuntimeError: The grpc package installed is at version ...`

Generated code records the `grpcio` version it was made with and refuses to run against an older runtime. **Diagnose:** compare `grpcio` and `grpcio-tools` versions in `pyproject.toml`. **Fix:** keep them pinned to the same version, run `uv sync`, then regenerate.

## Knowledge check

1. You rename `language` to `locale` but keep `= 2`. Do old clients break?
2. Is a protobuf message on the wire encrypted?
3. Why must a deleted field number never be reused?

<details>
<summary>Answers</summary>

1. Not on the wire - the number is unchanged. Source code using the old name must be updated.
2. No. Protobuf is an encoding. Use TLS for confidentiality.
3. Old clients still send that number with the old meaning; a new field with the same number would misinterpret it.

</details>

## Done when

`generate_proto.py --check` prints `OK`, and you can decode `0a 03 41 64 61` by hand.

Next: [05 · Your First gRPC Call](05-first-grpc-call.md)
