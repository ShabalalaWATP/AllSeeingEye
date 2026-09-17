# syntax=docker/dockerfile:1
# Build context: the repository root (docker build -f frontend/Dockerfile .).
# Build the SPA and the same standard Caddy release with patched, locked Go
# dependencies. The final image retains the upstream runtime and shared Caddyfile.

FROM golang:1.26.6-alpine3.23@sha256:5978cc992ad5ef96a7469713c8af849c1433824761ce3be2c56381403cd8d9a3 AS caddy-build
ENV CGO_ENABLED=0 GOTOOLCHAIN=local
WORKDIR /build
COPY infra/caddy-build/go.mod infra/caddy-build/go.sum ./
RUN go mod download && go mod verify
COPY infra/caddy-build/main.go ./
# Match the official binary's module/build selection and retain its version metadata.
RUN go build -mod=readonly -trimpath -buildvcs=false \
    -tags=nobadger,nomysql,nopgx -ldflags='-s -w' -o /out/caddy .

FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS build
ENV CI=true
WORKDIR /app
RUN npm install -g pnpm@11.25.0
# .npmrc carries the patient retry settings; pnpm-workspace.yaml the build-script allow list.
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM caddy:2.11.4-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648
# Refresh inherited Alpine packages while retaining the reviewed upstream base.
RUN apk upgrade --no-cache
COPY --from=caddy-build /out/caddy /usr/bin/caddy
# COPY replaces the upstream inode, including the capability needed on low ports.
RUN setcap cap_net_bind_service=+ep /usr/bin/caddy
COPY infra/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
