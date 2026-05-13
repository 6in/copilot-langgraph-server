FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# HTTP プロキシ対応 — build args として受け、ENV に反映する。
# apt / curl / npm / uv はいずれも HTTP_PROXY/HTTPS_PROXY/NO_PROXY (大文字/小文字)
# を honor する。プロキシ環境下では --build-arg HTTP_PROXY=... で渡す、未指定なら no-op。
ARG HTTP_PROXY=
ARG HTTPS_PROXY=
ARG NO_PROXY=
ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY}

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
# npm は環境変数だけでは proxy を読まないバージョンがあるため、明示的に npm config も設定する。
# HTTPS_PROXY が空文字なら設定スキップ (proxy 未使用環境)。
RUN if [ -n "${HTTPS_PROXY}" ]; then \
      npm config set proxy "${HTTP_PROXY}" && \
      npm config set https-proxy "${HTTPS_PROXY}" && \
      ([ -n "${NO_PROXY}" ] && npm config set noproxy "${NO_PROXY}" || true); \
    fi && \
    npm install -g @anthropic-ai/claude-code

WORKDIR /mcp_server

CMD ["sh", "-c", "uv sync && uv run python server.py"]
