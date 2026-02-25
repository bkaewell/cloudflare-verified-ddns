# ───────────────────────────────────────────────────────────
# Multi-stage Dockerfile (Python 3.13 Alpine + uv)
# ───────────────────────────────────────────────────────────
# - Builder: uv installs deps/project → final drops uv toolchain
# - Uses system Python only (no managed downloads)
# - Excludes dev deps; separate caching for deps vs. code
# - Security: non-root + owned writable dirs
# - Fast startup via .pyc + copy mode
# ───────────────────────────────────────────────────────────

# Builder stage
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

# uv + Python settings
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON_PREFERENCE=only-system \
    UV_NO_BUILD_ISOLATION=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Cache deps layer
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable

# Install project after code copy
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Runtime stage
FROM python:3.13-alpine AS prod

WORKDIR /app

# Copy venv (deps + installed project)
COPY --from=builder /app/.venv /app/.venv

# Non-root user + app-specific cache dir (customize path as needed)
RUN addgroup -S app && adduser -S app -G app && \
    mkdir -p /app/cache/cloudflare_verified_ddns && \
    chown -R app:app /app

# Copy code with ownership
COPY --from=builder --chown=app:app /app/src /app/src

USER app

# Runtime env (venv activated + production Python defaults)
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src"

# Command (customize module/entrypoint)
CMD ["python", "-m", "cloudflare_verified_ddns.__main__"]
