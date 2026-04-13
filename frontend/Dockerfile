# Stage 1: dev (Bun dev server)
FROM oven/bun:1-alpine AS dev
WORKDIR /app
COPY package.json bun.lock* bun.lockb* ./
RUN bun install
COPY . .
EXPOSE 5173
CMD ["bun", "run", "dev", "--", "--host", "0.0.0.0"]

# Stage 2: builder (Bun でビルド)
FROM oven/bun:1-alpine AS builder
WORKDIR /app
COPY package.json bun.lock* bun.lockb* ./
RUN bun install --frozen-lockfile || bun install
COPY . .
ARG VITE_APP_BASE=/orochi
ENV VITE_APP_BASE=$VITE_APP_BASE
RUN bun run build

# Stage 3: prod (nginx で静的ファイル配信)
FROM nginx:1.27-alpine AS prod
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
