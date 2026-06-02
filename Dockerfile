# ── Stage 1: dependency installer ─────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Bring in uv from its official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install production dependencies into an isolated venv.
# Copying requirements first lets Docker cache this layer when only app code changes.
COPY requirements.txt .
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv -r requirements.txt


# ── Stage 2: runtime image ─────────────────────────────────────────────────────
FROM python:3.13-slim

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy the pre-built venv from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY app/ ./app/

# Create persistent-data directories and hand ownership to appuser
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

USER appuser

# Put the venv on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Use exec form so uvicorn receives SIGTERM directly (clean shutdown)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
