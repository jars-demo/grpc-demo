# The workshop website as static files behind nginx. Build from the repository root (the site
# reads workshop/, docs/ and challenge/scenarios/ at build time):
#
#   docker build -f frontend/Dockerfile -t grpc-demo-web .

FROM node:26.11.1-alpine AS build
WORKDIR /repo/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY frontend/ ./
COPY workshop/ /repo/workshop/
COPY docs/ /repo/docs/
COPY challenge/scenarios/ /repo/challenge/scenarios/
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.29-alpine AS runtime
LABEL org.opencontainers.image.title="grpc-demo-web" \
      org.opencontainers.image.description="gRPC & HTTPS workshop website (static)" \
      org.opencontainers.image.source="https://github.com/jars-demo/grpc-demo" \
      org.opencontainers.image.licenses="MIT"
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/frontend/out /usr/share/nginx/html
EXPOSE 8080
