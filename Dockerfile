# One image for every Python service (gRPC server, REST API) plus a `toolbox` target for running
# the clients, examples, certificate lab and challenge inside Docker. Build from the repo root:
#
#   docker build -t grpc-demo-service .                 # runtime (services)
#   docker build --target toolbox -t grpc-demo-toolbox .
#
# Certificates are NEVER copied into an image (.dockerignore excludes certs/out). Compose mounts
# only the files each container needs, read-only, at runtime.

ARG PYTHON_IMAGE=python:3.13.16-slim-trixie

# --- build: resolve dependencies with uv into a virtualenv -----------------------------------
FROM ${PYTHON_IMAGE} AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# --- runtime: the services, nothing else ------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime
LABEL org.opencontainers.image.title="grpc-demo-service" \
      org.opencontainers.image.description="gRPC & HTTPS workshop: gRPC server and REST API (educational)" \
      org.opencontainers.image.source="https://github.com/jars-demo/grpc-demo" \
      org.opencontainers.image.licenses="MIT"
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY services/ /app/services/
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/services:/app/services/generated" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER 10001
# Compose chooses the process: `python -m grpc_server` or `python -m rest_api`.
CMD ["python", "-m", "grpc_server"]

# --- toolbox: runtime + openssl/curl + examples, certificate lab and challenge ----------------
FROM runtime AS toolbox
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssl curl \
 && rm -rf /var/lib/apt/lists/*
COPY examples/ /app/examples/
COPY certs/scripts/ /app/certs/scripts/
COPY certs/openssl/ /app/certs/openssl/
COPY services/proto/ /app/services/proto/
USER 10001
CMD ["python", "-m", "grpc_client", "--help"]
