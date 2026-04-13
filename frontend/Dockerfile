# Stage 1: dev (既存の node:22-alpine を維持して docker-compose.yml は動作継続)
FROM node:22-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Stage 2: builder (Bun でビルド)
FROM oven/bun:1-alpine AS builder
WORKDIR /app
COPY package*.json bun.lockb* ./
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
