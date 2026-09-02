# ADR 0002: Durable database

Status: Accepted (proposed 2 September 2026, accepted by Alex 3 September 2026)

## Context

The durable data is small and relational: users, sessions, audit events, the source registry, encrypted credentials, areas of interest (polygons), collection plans, indicators, alerts, reports, frozen evidence (with geometry), and hourly baseline aggregates. Live feed data is explicitly not stored (see ADR 0003). The app runs on a single home machine or server under Docker Compose.

## Options

1. **PostgreSQL 16 with PostGIS**, run as a container. Real geospatial queries (AOI containment, evidence within an area), strong migrations story with Alembic, optional pgvector later for semantic search of reports, robust backups with `pg_dump`.
2. **SQLite** (with SpatiaLite for geometry). Zero infrastructure, one file, fine for a single writer. Geometry support is awkward on Windows, concurrent writes from collectors and users are serialised, and moving to PostgreSQL later means migration work.

## Decision

Option 1 for the running application. SQLAlchemy 2.0 async with repository classes behind ports; the unit-test suite runs against SQLite in memory for speed where geometry is not involved, and against a PostGIS container in CI for the geospatial repositories.

## Consequences

- Docker is a development prerequisite (Docker Desktop on Windows).
- Backups are a scheduled `pg_dump` into a mounted folder with a retention rule.
- The schema stays deliberately small; every new table needs a justification in the implementation plan.
