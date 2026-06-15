FROM python:3.13-slim

# Set working directory inside the container
WORKDIR /app

# Install uv inside the container
# Reference: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (so Docker caches this layer)
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy the rest of the code
COPY . .

# Expose the port
EXPOSE 8000