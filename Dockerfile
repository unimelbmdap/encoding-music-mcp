# syntax=docker/dockerfile:1

# Use specific UV version for reproducibility
FROM ghcr.io/astral-sh/uv:0.5.11-python3.12-bookworm-slim AS builder

# Install build dependencies for compiling Python packages (verovio needs swig + C++)
# git is needed for uv to install packages from GitHub repositories
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        swig \
        git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Copy source code (needed for package build)
COPY src/ src/
COPY README.md ./

# Install production dependencies and package
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Final stage - minimal runtime image
FROM python:3.12-slim-bookworm

# Install only required system dependencies
# (none needed for this project, but keeping structure for future additions)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r -g 1000 mcp && \
    useradd -r -u 1000 -g mcp -s /bin/bash -m mcp

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=mcp:mcp /app/.venv /app/.venv

# Copy installed package
COPY --from=builder --chown=mcp:mcp /app/src /app/src

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create directory for user-provided MEI files (optional)
RUN mkdir -p /data && chown mcp:mcp /data

# Switch to non-root user
USER mcp

# Health check - verify HTTP server is responding
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/mcp')"

# Run the MCP server
ENTRYPOINT ["/app/.venv/bin/encoding-music-mcp"]
