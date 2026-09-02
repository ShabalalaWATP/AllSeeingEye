# ADR 0006: Modular monolith with in-process collectors

Status: Accepted (proposed 2 September 2026, accepted by Alex 3 September 2026)

## Context

The application has three natural runtime concerns: serving the API and SSE, polling feeds and running the pipeline, and generating reports. A hobby deployment on one machine should be simple to run, debug and back up.

## Options

1. **One FastAPI process** hosting the API, the collectors (asyncio tasks driven by an in-process scheduler) and report generation, organised internally into domain, application, adapters and API layers.
2. **API plus a separate worker** (Celery, ARQ or a plain asyncio worker) communicating through Redis. Cleaner isolation, but two processes, a broker, and duplicated configuration for a workload that a single process handles comfortably.
3. **Microservices per feed category.** Not justified at any foreseeable scale.

## Decision

Option 1, with hard internal boundaries enforced by import-linting (`import-linter`) so that the collectors and pipeline can be lifted into a worker later. Report generation runs as a background task within the process with a concurrency cap; long generations stream progress over SSE.

## Consequences

- One container to run, one log to read, one process to profile.
- A crash in a connector must never take the process down: connectors run under supervision with timeouts and circuit breakers.
- Moving to option 2 later means implementing the Redis-backed `EventStore` and `EventBus` adapters and a worker entry point; the application code does not change.
