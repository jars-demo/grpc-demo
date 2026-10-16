# 13 · Final Challenge

> ⏱ 25 minutes · Six broken secure connections. Reproduce, diagnose, fix, verify - without weakening security.

## Learning objectives

- Apply the chapter 11 method to unfamiliar failures.
- Fix each problem at its cause, using only the client's connection profile.
- Prove the fix with an automatic check that also rejects insecure shortcuts.

## Prerequisites

Chapters 08-12. The stack is running (`uv run python scripts/tasks.py up`).

## Concept: the rules

Each scenario is a **connection profile** - a small TOML file with the target, the CA to trust, an optional client certificate and a deadline - and a fixed client command. The servers, the certificates and the command are correct and must not change, just as a client team cannot edit someone else's servers. You may change **only** your copy of the profile, `challenge/work/NN.toml`.

```toml
# challenge/work/01.toml (example layout)
target = "localhost:50051"
ca = "certs/out/....crt"
cert = "certs/out/....crt"     # optional: mutual TLS
key = "certs/out/....key"      # optional: mutual TLS
deadline_seconds = 5
```

`check` passes a scenario only when the call succeeds **and**:

- it uses TLS or mutual TLS, as the scenario requires - never plaintext;
- it trusts exactly the workshop CA, `certs/out/ca.crt`;
- the deadline stays bounded.

There is no way to turn off certificate verification: the profile format does not have such a key, and the client does not have such an option.

## Exercise

### 1. Create your working copies

```bash
uv run python -m challenge start
uv run python -m challenge list
```

**Expected:**

```text
  01  The certificate nobody trusts      ready        A client that worked yesterday now fails to connect to the TLS endpoint.
  02  Right server, wrong name           ready        Someone 'optimized' the target to an IP address to skip DNS. Now TLS fails.
  03  The door that asks for ID          ready        A new service connects to the mutual TLS port and is disconnected immediately.
  04  Same name, wrong signature         ready        The client presents a certificate with the right name, but the server still hangs up.
  05  Authenticated is not authorized    ready        The mutual TLS handshake succeeds, but reading server stats is refused.
  06  Impatient client                   ready        A known-slow call (about 0.8 s) fails every time, but the server is healthy.
```

Without Python on your machine, run every `challenge` command in the challenge container instead - it shares `grpc-server`'s network, so `localhost` means the same thing:

```bash
docker compose --profile tools run --rm challenge start
docker compose --profile tools run --rm challenge run 01
```

### 2. Work through each scenario

For each number `NN` from `01` to `06`:

1. **Reproduce:** `uv run python -m challenge run NN` - a real call, a real error.
2. **Read** the status and the details to the end.
3. **Inspect:** the profile (`challenge/work/NN.toml`), the certificates (`uv run python certs/scripts/certs.py inspect <name>`), the server log (`docker compose logs grpc-server --since 5m`).
4. **Identify** the cause, in one sentence.
5. **Fix** the profile.
6. **Re-run:** `uv run python -m challenge run NN`.
7. **Verify:** `uv run python -m challenge check NN`.

Stuck? `uv run python -m challenge hint NN` reveals one more hint each time you run it (three per scenario). `uv run python -m challenge reset NN` restores the broken profile.

**Expected when you are done:**

```bash
uv run python -m challenge check all
```

```text
  01 The certificate nobody trusts      PASS
  02 Right server, wrong name           PASS
  03 The door that asks for ID          PASS
  04 Same name, wrong signature         PASS
  05 Authenticated is not authorized    PASS
  06 Impatient client                   PASS

6/6 passed
```

### 3. Try a shortcut (and watch it fail)

Once scenario 06 passes, set its `deadline_seconds = 60` and run `check 06` again:

```text
  06 Impatient client                   FAIL  deadline_seconds must stay bounded (at most 5 s for this call)
```

Or remove the `ca` line's value in scenario 01 (`ca = ""`, meaning "use gRPC's bundled public roots"):

```text
  01 The certificate nobody trusts      FAIL  the profile must trust the workshop CA explicitly (ca = "certs/out/ca.crt")
```

A connection that "works" is not the goal. A connection that works *and* is still secure is.

## What just happened

Every failure was real: the challenge runner calls the same client as the rest of the workshop (`challenge/__main__.py`), against the same servers, and checks the result. You used the status code to locate the layer, the details or the server log to find the cause, and inspection tools to confirm it before changing anything.

## Common failure: changing several things at once

Swapping the CA, the target and the certificate in one edit "to be sure". The scenario passes but you do not know which change mattered, and next time you will not either. **Fix:** one change, re-run, read.

## Solutions

Try every scenario before opening these.

<details>
<summary>01 · The certificate nobody trusts</summary>

**Symptom:** `UNAVAILABLE ... CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`.
**Cause:** the profile trusts `certs/out/rogue-ca.crt`, but the server certificate was issued by the workshop CA (`certs.py inspect server` shows `issuer=CN=JARS Workshop Local CA,...`).
**Fix:** `ca = "certs/out/ca.crt"`.

</details>

<details>
<summary>02 · Right server, wrong name</summary>

**Symptom:** `UNAVAILABLE ... Hostname Verification Check failed`.
**Cause:** the target is `127.0.0.1:50051`; the certificate's SAN lists `DNS:localhost, DNS:grpc-server, DNS:rest-https` and no IP address.
**Fix:** `target = "localhost:50051"`. (The other correct fix, if you owned the server, would be reissuing the certificate with `IP:127.0.0.1` in its SAN. Overriding the name the client checks is not a fix.)

</details>

<details>
<summary>03 · The door that asks for ID</summary>

**Symptom:** `UNAVAILABLE ... End of TCP stream` (or `Connection aborted`). Server log: `PEER_DID_NOT_RETURN_A_CERTIFICATE`.
**Cause:** port 50052 requires a client certificate; the profile has none.
**Fix:** add `cert = "certs/out/client.crt"` and `key = "certs/out/client.key"`.

</details>

<details>
<summary>04 · Same name, wrong signature</summary>

**Symptom:** `UNAVAILABLE`. Server log: `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`.
**Cause:** `rogue-client.crt` says `CN=workshop-client`, but it was issued by the rogue CA, which the server does not trust.
**Fix:** `cert = "certs/out/client.crt"`, `key = "certs/out/client.key"`.

</details>

<details>
<summary>05 · Authenticated is not authorized</summary>

**Symptom:** `PERMISSION_DENIED: identity 'workshop-client' is authenticated but not authorized for AdminService`.
**Cause:** the handshake succeeded; the authorization policy (`GRPC_ADMIN_IDENTITIES`) allows only `workshop-admin`.
**Fix:** `cert = "certs/out/admin.crt"`, `key = "certs/out/admin.key"`. In a real system you might instead change the policy - deliberately, not by sharing the admin key.

</details>

<details>
<summary>06 · Impatient client</summary>

**Symptom:** `DEADLINE_EXCEEDED` after 0.3 s.
**Cause:** the call takes about 0.8 s; the profile's deadline is 0.3 s.
**Fix:** `deadline_seconds = 2` (any value from about 1 to 5 passes). Bounded headroom, not "no deadline".

</details>

## Knowledge check

1. In which two scenarios did the server log tell you more than the client?
2. Which scenario's failure was not a TLS failure at all?
3. Why does `check` reject `ca = ""` even when the call would fail anyway?

<details>
<summary>Answers</summary>

1. 03 and 04: the server rejected the client certificate during the handshake.
2. 05 (authorization) and 06 (deadline) both happened after a successful handshake.
3. The rules check the *configuration*, not just the outcome: trusting anything other than the intended CA is a defect even when it happens to fail today.

</details>

## Done when

`uv run python -m challenge check all` prints `6/6 passed`.

Congratulations - you have taken a request from plain HTTP to authenticated, authorized RPC over mutual TLS, and you can diagnose the failures that matter along the way. Ideas for going further are in [docs/architecture.md](../docs/architecture.md#going-further) and [docs/security.md](../docs/security.md#before-production).
