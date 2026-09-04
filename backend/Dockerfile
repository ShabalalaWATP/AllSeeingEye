FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first so the layer is cached independently of the source.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 ase \
    && mkdir -p /app/data \
    && chown -R ase:ase /app
USER ase

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status == 200 else 1)"

# Behind Caddy the TCP peer is always the proxy, so uvicorn must read X-Forwarded-For from
# it or every client shares one rate-limit bucket and one audit IP. The API port is not
# published, so trusting the whole compose network is safe; narrow it if that changes.
CMD ["sh", "-c", "ase migrate && uvicorn ase.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips \"${ASE_FORWARDED_ALLOW_IPS:-*}\""]
