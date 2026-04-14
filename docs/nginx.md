# Nginx Reverse-Proxy Setup

## Overview

nginx strips the path prefix (e.g. `/orochi`) before forwarding requests to FastAPI.
FastAPI routes remain unchanged at `/api/...` — no route prefixing needed in Python code.

The `root_path` setting in FastAPI (`APP_PREFIX` env var) only affects OpenAPI docs URLs
(`/orochi/docs`, `/orochi/redoc`) so they generate correct `servers` entries. It does NOT
change how routes are defined or matched.

Frontend API calls use relative paths (`./api/...`) so the browser resolves them correctly
against the current page origin + base path regardless of what prefix is in the URL.

## Nginx Config Example

```nginx
server {
    listen 80;
    server_name example.com;

    location /orochi/ {
        # Trailing slash on proxy_pass strips the /orochi prefix before forwarding.
        proxy_pass http://backend:8000/;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /orochi;
    }
}
```

Key: `proxy_pass http://backend:8000/;` — the trailing `/` causes nginx to strip the
matched location prefix (`/orochi`) before forwarding. FastAPI receives `/api/...` paths
as-is, matching its registered routes.

## Environment Variables

| Variable | Where | Example | Purpose |
|----------|-------|---------|---------|
| `APP_PREFIX` | FastAPI (server) | `/orochi` | Sets `root_path` so OpenAPI docs generate correct URLs |
| `VITE_APP_BASE` | Vite (build/dev) | `/orochi` | Asset URL prefix in built HTML (`<script src="/orochi/assets/...">`) and dev proxy key |

## Dev vs Prod

### Development (Vite dev server)

```bash
VITE_APP_BASE=/orochi bun run dev
# or
VITE_APP_BASE=/orochi npm run dev
```

- Vite serves the app at `http://localhost:5173/orochi/`
- Vite proxy matches `/orochi/api` and rewrites to `/api` before forwarding to FastAPI
- FastAPI runs normally at `localhost:8000` without any prefix

### Production (built assets served by FastAPI)

```bash
APP_PREFIX=/orochi uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

Then build the frontend with the matching base:

```bash
VITE_APP_BASE=/orochi bun run build
# or
VITE_APP_BASE=/orochi npm run build
```

FastAPI serves `frontend/dist/` at `/react` and `static/` at `/`. nginx sits in front
and strips `/orochi` before all requests reach FastAPI.

## Docker Compose Snippet

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - backend

  backend:
    build: .
    environment:
      - APP_PREFIX=/orochi
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres?sslmode=disable
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
```

Mount the nginx config shown in the example above as `./nginx.conf`.

## SPA Fallback (Phase 25)

React Router v6(HTML5 History API) を使うため、`/orochi/chat/abc-123` のような
deep URL を直接開いたときに nginx が 404 を返さないよう `try_files` を設定する。

```nginx
location /orochi/ {
  # 既存のプレフィックス strip + proxy_pass 設定はそのまま
  # SPA fallback を追加:
  try_files $uri $uri/ /orochi/index.html;
}
```

注意:
- `/orochi/api/` など API パスには fallback が適用されないよう location 分離を維持する
- 開発環境(Vite dev server)は自動的に fallback するためこの設定は production のみ必要
