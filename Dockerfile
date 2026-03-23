FROM python:3.11-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY openobserve_mcp ./openobserve_mcp

RUN python -m pip install --upgrade pip build \
    && python -m build --wheel --outdir /tmp/dist


FROM python:3.11-slim AS runtime

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

LABEL io.modelcontextprotocol.server.name="io.github.alilxxey/openobserve-community-mcp"
LABEL org.opencontainers.image.source="https://github.com/alilxxey/openobserve-community-mcp"

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY --from=build /tmp/dist/*.whl /tmp/

RUN python -m pip install /tmp/*.whl \
    && rm -f /tmp/*.whl

USER appuser

ENTRYPOINT ["openobserve-mcp"]
