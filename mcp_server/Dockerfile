FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install Node.js 20 via official binary archive (avoids nodesource repo network issues)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates xz-utils && \
    rm -rf /var/lib/apt/lists/*

# Detect architecture and download matching Node.js binary
RUN ARCH=$(dpkg --print-architecture) && \
    case "$ARCH" in \
      amd64) NODE_ARCH="x64" ;; \
      arm64) NODE_ARCH="arm64" ;; \
      *) echo "Unsupported arch: $ARCH" && exit 1 ;; \
    esac && \
    NODE_VERSION="v20.19.1" && \
    curl -fsSL "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" \
      -o /tmp/node.tar.xz && \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && \
    rm /tmp/node.tar.xz

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /mcp_server

CMD ["sh", "-c", "uv sync && uv run python server.py"]
