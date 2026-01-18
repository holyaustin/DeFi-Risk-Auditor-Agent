# Use Python 3.11 with UV
FROM ghcr.io/astral-sh/uv:python3.11-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 agent
USER agent
WORKDIR /home/agent

# Copy project files
COPY --chown=agent:agent pyproject.toml uv.lock README.md ./
COPY --chown=agent:agent src src/
COPY --chown=agent:agent hardhat hardhat/
COPY --chown=agent:agent .env.example ./

# Install Python dependencies
RUN \
    --mount=type=cache,target=/home/agent/.cache/uv,uid=1000 \
    uv sync --frozen

# Install Node.js dependencies
WORKDIR /home/agent/hardhat
RUN npm ci --only=production

# Return to main directory
WORKDIR /home/agent

# Expose port
EXPOSE 9009

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:9009/.well-known/agent-card.json || exit 1

# Run the application
ENTRYPOINT ["uv", "run", "src/server.py"]
CMD ["--host", "0.0.0.0", "--port", "9009"]