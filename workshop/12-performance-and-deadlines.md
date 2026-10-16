# 12 · Performance and Deadlines

> ⏱ 15 minutes · Measure honestly, find what really costs time, and choose deadlines on purpose.

## Learning objectives

- Run a fair latency comparison and state what it does and does not show.
- Show the cost of connection setup (TCP + TLS handshake) versus reusing a connection.
- Choose deadlines from measured latency, and explain what happens on both sides when one expires.

## Prerequisites

Chapters 06, 07 and 09. The stack is running.

## Concept

### Measuring responsibly

A benchmark answers a narrow question: *this* client, *this* server, *this* payload, *this* network, *this* concurrency. Before you trust a number:

- **Warm up.** The first call pays for connecting, the TLS handshake and lazy initialization.
- **Report percentiles**, not just the mean. p50 is the typical call; p95/p99 are what users notice.
- **Change one variable at a time.** Protocol version, serialization, framework and connection reuse all differ between our REST and gRPC services.
- **Repeat.** Background load on a laptop moves numbers by tens of percent.

### Deadlines

A **deadline** is an absolute point in time by which the caller stops waiting. gRPC sends it to the server in the `grpc-timeout` header, so:

- the client gets `DEADLINE_EXCEEDED` at the deadline, whatever the server is doing;
- the server can see the call has ended (`context.add_callback`, `context.is_active()`) and stop working - this repository's servicers do (`_Lifetime.wait`);
- a server calling other services can pass the *remaining* time on, so a whole chain gives up together.

Without a deadline, a call to a hung server waits forever and holds resources on both sides. Every call in this repository passes `timeout=`.

## Exercise

### 1. Reused connections

```bash
uv run python examples/latency_compare.py --calls 200
```

**Observed on the author's machine** (Windows 11, Docker Desktop; yours will differ):

```text
200 sequential calls each, after 20 warm-up calls, one reused connection:

gRPC  SayHello (TLS)   n=200   p50=  1.50ms  p95=  2.10ms  mean=  1.56ms  max=  3.34ms
REST  POST (HTTPS)     n=200   p50=  2.75ms  p95=  3.97ms  mean=  2.88ms  max= 11.13ms
```

Run it three times. Note how much the numbers move between runs. Against the same services running directly on the host (no Docker port forwarding), the same machine measured gRPC p50 at 0.44 ms - a 3× difference that has nothing to do with either protocol.

### 2. New connection per call

```bash
uv run python examples/latency_compare.py --calls 100 --warmup 5 --fresh-connections
```

**Observed on the author's machine:**

```text
100 sequential calls each, after 5 warm-up calls, a new connection per call:

gRPC  SayHello (TLS)   n=100   p50=  5.72ms  p95=  7.02ms  mean=  5.71ms  max=  8.66ms
REST  POST (HTTPS)     n=100   p50= 22.97ms  p95= 32.81ms  mean= 20.61ms  max= 34.21ms
```

Every call now pays for TCP setup and a full TLS handshake - several times the cost of the call itself, even on loopback. Across a real network each handshake also costs extra round trips. **Lesson: create a channel (or HTTP client) once and reuse it.**

Read `rest_call()` in `examples/latency_compare.py` before concluding anything about REST from that second line. A new `httpx.Client` also builds a new TLS context and loads the CA file every time; much of the gap is that client-side setup, not HTTP/1.1 or JSON. That is exactly the kind of hidden variable that makes naive benchmarks misleading.

### 3. A deadline that is too tight

```bash
uv run python -m grpc_client --deadline 0.5 hello --delay-ms 800
uv run python -m grpc_client --deadline 2 hello --delay-ms 800
```

**Expected:** the first fails after about 0.5 s:

```text
RPC failed: DEADLINE_EXCEEDED
  details: Deadline Exceeded
  meaning: The deadline passed before the server answered. The server may still have done the work. (REST: client timeout / 504)
```

the second succeeds after about 0.8 s. "The server may still have done the work" matters: for a call that changes state (a payment, an order), a deadline exceeded does not mean "nothing happened". Such calls need idempotency keys or a way to check the outcome before retrying.

### 4. The REST equivalent

```bash
uv run python examples/rest_client.py https://localhost:8443/v1/greetings --name Ada --delay-ms 800 --timeout 0.5
```

**Expected:** `timed out after 0.5s`. HTTP has no standard header that carries the client's deadline to the server; the REST server only finds out when the client disconnects.

### 5. Choose a deadline

From step 1, p95 for `SayHello` is a few milliseconds. A deadline should cover normal slow cases with headroom, but be far below "a user gave up": for this call, somewhere around 100 ms to 1 s would be reasonable on a LAN. Measure p99 under realistic load, add headroom, and set the deadline per method - a report generation RPC and a health check need very different values.

## What just happened

You measured instead of assuming, and found that connection setup and environment (Docker networking, client library setup) dwarfed protocol differences for small payloads. You also saw deadlines enforced on the client immediately and observed on the server, and why a timed-out mutating call is not proof that nothing happened.

## Common failure: retrying on every DEADLINE_EXCEEDED

Automatic retries of a timed-out call multiply load on a server that is already slow, and can repeat side effects. **Fix:** retry only idempotent calls, with backoff and a retry budget, and keep the overall deadline shared across retries.

## Knowledge check

1. Why does the first call in a benchmark need to be excluded?
2. A colleague reports "REST is 4× slower" from step 2. What do you ask?
3. What does the server know when the client's deadline passes?

<details>
<summary>Answers</summary>

1. It includes connection setup, the TLS handshake and lazy initialization, which later calls do not pay.
2. Whether each side reused its connection, what the client library does per connection, the payload size, how many runs, and whether the environment (Docker, network) was the same.
3. gRPC propagates the deadline, so the server sees the call become inactive and can stop working. Its own work may already have completed.

</details>

## Done when

You have run both latency modes at least twice, and produced one `DEADLINE_EXCEEDED` and one success for the same slow call.

Next: [13 · Final Challenge](13-final-challenge.md)
