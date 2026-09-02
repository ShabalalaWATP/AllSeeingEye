# ADR 0004: Realtime transport is Server-Sent Events

Status: Accepted (proposed 2 September 2026, accepted by Alex 3 September 2026)

## Context

Browsers need a continuous stream of new and expired events, alerts, source health and report-generation progress. The browser never streams data to the server; user actions are ordinary REST calls.

## Options

1. **Server-Sent Events (SSE)** over HTTP: one long-lived response per client, automatic reconnection with `Last-Event-ID`, trivially proxied by Caddy, simple to test.
2. **WebSockets**: bidirectional, slightly lower overhead, more moving parts (ping/pong, reconnection logic, proxy configuration, auth handshake).
3. **Polling**: simplest, but wasteful for flight and AIS layers and adds latency to alerts.

## Decision

Option 1 using `sse-starlette`. Clients subscribe with a filter (categories, bounding box or country, time window); the server batches heavy layers into compact JSON frames at most every few seconds. Authentication uses the short-lived access token passed at connection time; the stream is closed when the token expires and the client reconnects with a fresh one.

## Consequences

- Heavy layers (aircraft, fires) send deltas keyed by event id; the client keeps its own bounded mirror of the live store.
- If bidirectional needs ever appear (collaborative editing), WebSockets can be added for that feature alone.
