FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base



# Setup a non-root user
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

# Install system dependencies (Tesseract OCR and curl for health checks)
# Clean up apt cache to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        curl \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*



WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# ------------------------------------------------------------------------------
# Dependencies stage - install project dependencies
# ------------------------------------------------------------------------------
FROM base AS dependencies

# Omit development dependencies
ENV UV_NO_DEV=1

# Install the project's dependencies using the lockfile and settings
# Using cache mount with proper permissions
RUN --mount=type=cache,target=/home/nonroot/.cache/uv,uid=999,gid=999 \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# ------------------------------------------------------------------------------
# Development stage
# ------------------------------------------------------------------------------
FROM dependencies AS development

# Include development dependencies for dev stage
ENV UV_NO_DEV=0

# Copy the rest of the project source code
COPY --chown=nonroot:nonroot . /app

# Install project with dev dependencies
RUN --mount=type=cache,target=/home/nonroot/.cache/uv,uid=999,gid=999 \
    uv sync --locked

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint
ENTRYPOINT []

# Use the non-root user
USER nonroot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run with hot-reloading for development
CMD ["uvicorn", "src.image_service.app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

# ------------------------------------------------------------------------------
# Production stage
# ------------------------------------------------------------------------------
FROM dependencies AS production

# Copy only the necessary application code
COPY --chown=nonroot:nonroot ./src /app/src

# Install the project
RUN --mount=type=cache,target=/home/nonroot/.cache/uv,uid=999,gid=999 \
    uv sync --locked

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint
ENTRYPOINT []

# Use the non-root user
USER nonroot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run with production server
CMD ["uvicorn", "src.image_service.app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]