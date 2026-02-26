# ───────────────────────────────────────────────────────────
# Multi-stage Dockerfile (Python 3.13 Alpine + uv)
# ───────────────────────────────────────────────────────────
# - Builder: uv installs deps/project → final drops uv toolchain
# - Uses system Python only (no managed downloads)
# - Excludes dev deps and project install (runtime imports source directly)
# - Security: non-root + only dedicated writable cache dir
# - Optimized for minimal runtime size
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

# Runtime stage
FROM python:3.13-alpine AS prod

WORKDIR /app

RUN addgroup -S app && adduser -S app -G app && \
    mkdir -p /app/cache/cloudflare_verified_ddns && \
    chown app:app /app/cache/cloudflare_verified_ddns

# Copy venv (deps only)
COPY --from=builder --chown=app:app /app/.venv /app/.venv
# Copy app code
COPY --chown=app:app app/ /app/app/

USER app

# Runtime env (venv activated + app on import path)
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/app"

# Entrypoint
CMD ["python", "-m", "app.main"]
