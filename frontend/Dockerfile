# syntax=docker/dockerfile:1
# Build context: the repository root (docker build -f frontend/Dockerfile .).
# Stage 1 compiles the SPA; stage 2 serves the static bundle through Caddy using
# the shared infra/Caddyfile, which also proxies /api to the backend.

FROM node:22-alpine AS build
ENV CI=true
WORKDIR /app
RUN npm install -g pnpm@11.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM caddy:2-alpine
COPY infra/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
