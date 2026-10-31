# ---------------------------------------------------------------------------
# Backend image: Python 3.14 + uv + FastAPI
# Build:  docker build -t todo-backend ./backend
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

# 1) Install dependencies FIRST, using only the lock files.
#    Docker caches this layer, so editing app code doesn't reinstall packages.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# 2) Then copy the application code
COPY app ./app

# Run as a non-root user (good security practice).
# Data lives in Postgres, so the app needs no writable folders.
RUN useradd --create-home appuser
USER appuser

# Put the venv's executables (fastapi, uvicorn...) on PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Docker marks the container "healthy" once /api/health answers
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# `fastapi run` = production mode (no auto-reload), unlike `fastapi dev`
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
