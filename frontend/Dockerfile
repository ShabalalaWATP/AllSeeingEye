# syntax=docker/dockerfile:1
# Build context: the repository root (docker build -f frontend/Dockerfile .).
# Build the SPA and the same standard Caddy release with patched, locked Go
# dependencies. The final image retains the upstream runtime and shared Caddyfile.

FROM golang:1.27.0-alpine3.23@sha256:3747dcba41c8b0db3211fda4db61638b980e17ac5bb3c94460a975a9cfe19395 AS caddy-build
ENV CGO_ENABLED=0 GOTOOLCHAIN=local
WORKDIR /build
COPY infra/caddy-build/go.mod infra/caddy-build/go.sum ./
RUN go mod download && go mod verify
COPY infra/caddy-build/main.go ./
# Match the official binary's module/build selection and retain its version metadata.
RUN go build -mod=readonly -trimpath -buildvcs=false \
    -tags=nobadger,nomysql,nopgx -ldflags='-s -w' -o /out/caddy .

FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS build
ENV CI=true
WORKDIR /app
RUN npm install -g pnpm@11.25.0
# .npmrc carries the patient retry settings; pnpm-workspace.yaml the build-script allow list.
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
# Caddy serves the .br and .gz siblings directly (file_server precompressed).
RUN pnpm build && node scripts/precompress.js dist

FROM caddy:2.11.4-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648
# Refresh inherited Alpine packages while retaining the reviewed upstream base.
RUN apk upgrade --no-cache \
    && addgroup -S -g 10001 aseweb \
    && adduser -S -D -H -u 10001 -G aseweb aseweb
COPY --from=caddy-build /out/caddy /usr/bin/caddy
# COPY replaces the upstream inode, including the capability needed on low ports.
RUN setcap cap_net_bind_service=+ep /usr/bin/caddy
COPY infra/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
RUN chown -R 10001:10001 /data /config
USER 10001:10001
