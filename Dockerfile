# ============================================================
# Multi-stage Dockerfile for cloudflare-verified-ddns
# ============================================================
# Goals:
#   • Reproducible & cache-friendly builds
#   • Minimal final image size (alpine + only runtime deps)
#   • Security: non-root user in final stage
#   • Fast startup: bytecode compilation + copied dependencies
# ============================================================

# ───────────────────────────────────────────────────────────
# Stage 1: Build stage
# ───────────────────────────────────────────────────────────
# - Bootstraps a minimal Python environment using uv
# - Installs locked dependencies into a local virtualenv
# - Uses Docker build cache aggressively
# - Generates .pyc files for faster startup (trade-off: slightly larger image)
# ───────────────────────────────────────────────────────────
FROM python:3.13-alpine AS build

# --- Tools / Bootstrapping ---
# Using latest uv from official image (consider pinning digest or tag in production)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# --- Copy dependency manifests first (maximizes cache hits) ---
COPY pyproject.toml uv.lock ./

# Optional: bring in source only for editable-like install or pyright/mypy usage during build
# COPY src/ ./src/

# --- uv environment settings ---
# UV_COMPILE_BYTECODE=1     → generate .pyc → faster startup, slightly bigger layers
# UV_LINK_MODE=copy         → real files instead of symlinks (more portable / simpler COPY)
# UV_NO_MANAGED_PYTHON=1    → don't let uv try to download its own Python
# PYTHONDONTWRITEBYTECODE=1 → prevent .pyc generation during pip/uv install steps
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_MANAGED_PYTHON=1 \
    UV_NO_BUILD_ISOLATION=1 \
    PYTHONDONTWRITEBYTECODE=1

# ── Install locked dependencies only (no project code yet) ──
# This layer usually has excellent cache reuse
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable

# Optional: verify the environment (good for CI/debug, can be removed in final prod version)
# RUN uv python list && \
#     uv pip list --system && \
#     python -c "import fastapi, httpx, pydantic; print('core imports ok')"

# ============================================================
# Stage 2: Runtime stage
# ============================================================
# - Minimal image: only Python runtime + our dependencies + application code
# - Non-root user + correct ownership on writable directories
# - Clean environment variables for production
# ============================================================
FROM python:3.13-alpine AS runtime

WORKDIR /app

# --- Copy only the virtualenv (bare minimum runtime dependencies) ---
COPY --from=build /app/.venv /app/.venv

# --- Create minimal non-root user + prepare cache directories ---
# Directories created here will be mounted later → must have correct ownership
RUN addgroup -S app && \
    adduser -S app -G app && \
    mkdir -p /app/cache/cloudflare_verified_ddns && \
    chown -R app:app /app

# --- Copy application source code (with correct ownership) ---
COPY --chown=app:app src/ /app/src/

# --- Switch to non-root user (security best practice) ---
USER app

# --- Activate virtual environment + runtime settings ---
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src${PYTHONPATH:+:${PYTHONPATH}}"

# --- Default command ---
# Uses the venv python automatically thanks to PATH
CMD ["python", "-m", "cloudflare_verified_ddns.__main__"]