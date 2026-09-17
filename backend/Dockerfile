FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.11.26@sha256:3d868e555f8f1dbc324afa005066cd11e1053fc4743b9808ca8025283e65efa5 /uv /uvx /bin/

WORKDIR /app

# Local media analysis uses system decoders inside a bounded worker process.
# Apply Debian security updates to packages inherited from the pinned base too.
RUN apt-get update \
    && apt-get upgrade --yes --no-install-recommends \
    && apt-get install --yes --no-install-recommends ffmpeg tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so the layer is cached independently of the source.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

# Runtime commands use the locked virtual environment, not pip's vendored toolchain.
# Remove build caches and the base-image pip to keep unused vulnerable vendors out.
RUN uv cache clean \
    && /usr/local/bin/python -m pip uninstall --yes pip

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
