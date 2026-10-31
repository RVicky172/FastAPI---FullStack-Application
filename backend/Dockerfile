# ---------------------------------------------------------------------------
# Backend image: Python 3.14 + uv + FastAPI
#
# The default CMD is production mode (`fastapi run`). docker-compose.yml
# overrides it with `fastapi dev` (auto-reload) for development.
# ---------------------------------------------------------------------------
FROM python:3.14-slim

# Copy the uv binary from its official image (no pip install needed)
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

WORKDIR /app

# UV_COMPILE_BYTECODE: precompile .py files -> faster container startup
# UV_LINK_MODE=copy:   needed because the uv cache is a separate mount
# UV_PYTHON_DOWNLOADS: use the image's Python, never download another one
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Non-root user (good security practice)
RUN useradd --create-home appuser

# 1) Install dependencies FIRST, using only the lock files.
#    Docker caches this layer, so editing app code doesn't reinstall packages.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# 2) Then copy the application code.
#    Owned by appuser so `docker compose watch` can sync edited files in.
COPY --chown=appuser:appuser app ./app

USER appuser

# Put the venv's executables (fastapi, uvicorn...) on PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Docker marks the container "healthy" once /api/health answers
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Production mode: no auto-reload
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
