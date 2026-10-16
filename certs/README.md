# Certificate lab

`scripts/certs.py` creates and manages the workshop's **local educational** certificates with OpenSSL. Every `openssl` command is printed as it runs.

```bash
uv run python certs/scripts/certs.py generate     # everything, into certs/out/
uv run python certs/scripts/certs.py list         # files, common names, issuers, expiry
uv run python certs/scripts/certs.py inspect server
uv run python certs/scripts/certs.py verify       # each certificate against the workshop CA
uv run python certs/scripts/certs.py rotate server
uv run python certs/scripts/certs.py regenerate   # new CA and everything else
uv run python certs/scripts/certs.py clean
```

- `openssl/ca.cnf` - the CA configuration: policies and the extension profiles (`v3_ca`, `server_ext`, `expired_server_ext`, `client_ext`).
- `scripts/certs.py` - the tool (Python standard library + the `openssl` binary).
- `out/` - generated output. **Ignored by Git and Docker. Never commit or share it.**

What each certificate is for, how keys are protected, and the issuance and rotation workflow: [docs/security.md](../docs/security.md).

No OpenSSL on your machine? Run the tool in the toolbox container, which includes it:

```bash
docker compose --profile tools run --rm --no-deps toolbox python certs/scripts/certs.py generate
```

> Never import `ca.crt` into your operating system or browser trust store. Its private key is stored unprotected in `out/ca.key`; anyone with that file could issue certificates your machine would trust.
