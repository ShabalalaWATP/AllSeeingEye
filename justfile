# Task runner. Install with `uv tool install rust-just` (or your package manager), then `just`.

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

# Run the API with auto-reload on http://localhost:8001
dev-api:
    cd backend && uv run uvicorn ase.main:app --reload --port 8001

# Run the web app with Vite on http://localhost:5173
dev-web:
    cd frontend && pnpm dev

# Run every test suite
test: test-api test-web

test-api:
    cd backend && uv run pytest

test-web:
    cd frontend && pnpm test

# Lint, type-check, import contracts and file length
check:
    cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run lint-imports
    cd frontend && pnpm lint && pnpm typecheck
    python scripts/check_file_length.py

# Apply database migrations
migrate:
    cd backend && uv run ase migrate

# Create the first administrator: just create-admin you@example.com "Your Name"
create-admin email name:
    cd backend && uv run ase create-admin --email {{email}} --display-name "{{name}}"

# Export the OpenAPI schema and regenerate the frontend API types
gen-api:
    cd backend && uv run ase export-openapi ../frontend/src/lib/api/openapi.json
    cd frontend && pnpm gen:api

# Start or stop the full stack (Docker Desktop must be running)
up:
    docker compose up --build -d

down:
    docker compose down
