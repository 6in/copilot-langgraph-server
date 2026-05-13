# Stage 1: dev (Bun dev server)
FROM oven/bun:1-alpine AS dev

# HTTP プロキシ対応 — build args として受け、ENV に反映する。
# プロキシ環境下では --build-arg HTTP_PROXY=... を指定、未指定なら空文字で no-op。
# Bun (1.0+) は HTTPS_PROXY/HTTP_PROXY/NO_PROXY を native に honor する。
ARG HTTP_PROXY=
ARG HTTPS_PROXY=
ARG NO_PROXY=
ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY}

WORKDIR /app
COPY package.json bun.lock* bun.lockb* ./
RUN --mount=type=cache,target=/root/.bun/install/cache bun install
COPY . .
EXPOSE 5173
CMD ["bun", "run", "dev", "--", "--host", "0.0.0.0"]

# Stage 2: builder (Bun でビルド)
FROM oven/bun:1-alpine AS builder
ARG HTTP_PROXY=
ARG HTTPS_PROXY=
ARG NO_PROXY=
ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY}

WORKDIR /app
COPY package.json bun.lock* bun.lockb* ./
RUN --mount=type=cache,target=/root/.bun/install/cache bun install --frozen-lockfile || bun install
COPY . .
ARG VITE_APP_BASE=/orochi
ENV VITE_APP_BASE=$VITE_APP_BASE
RUN bun run build

# Stage 3: prod (nginx で静的ファイル配信)
# 静的ファイル配信のみで外部ネットワーク不要のため proxy ARG は省略する。
FROM nginx:1.27-alpine AS prod
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
