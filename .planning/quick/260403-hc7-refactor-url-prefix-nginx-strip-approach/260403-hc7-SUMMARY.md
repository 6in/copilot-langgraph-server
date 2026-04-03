---
phase: quick
plan: 260403-hc7
subsystem: frontend, api, docs
tags: [url-prefix, nginx, vite, fastapi, relative-paths]
dependency_graph:
  requires: []
  provides: [nginx-strip-url-prefix-pattern]
  affects: [frontend/src/api/client.ts, frontend/vite.config.ts, app/api/main.py, docs/nginx.md]
tech_stack:
  added: []
  patterns: [relative-api-paths, nginx-prefix-strip, VITE_APP_BASE, FastAPI-root_path]
key_files:
  created:
    - docs/nginx.md
  modified:
    - frontend/src/api/client.ts
    - frontend/vite.config.ts
    - app/api/main.py
decisions:
  - "Relative ./api/ paths in client.ts: browser resolves against current origin+base, no hardcoded prefix in JS"
  - "VITE_APP_BASE controls both Vite `base` (asset URLs) and the dev proxy key+rewrite"
  - "APP_PREFIX sets FastAPI root_path only for OpenAPI docs — routes stay at /api/... unchanged"
  - "nginx trailing slash on proxy_pass strips location prefix before forwarding (e.g. /orochi/ -> /)"
metrics:
  duration: 8min
  completed: "2026-04-03T03:33:00Z"
  tasks_completed: 2
  files_changed: 4
---

# Quick 260403-hc7: Refactor URL Prefix — Nginx Strip Approach Summary

## One-liner

Switched frontend API calls to relative `./api/...` paths and added `VITE_APP_BASE`/`APP_PREFIX` env var support enabling nginx sub-path deployment without any route changes.

## What Was Done

Implemented the nginx-strip approach for sub-path deployment (e.g. `/orochi/`):

1. **client.ts**: Removed `VITE_BASE_URL` entirely. All 15 API paths now use `./api/...` (relative), letting the browser resolve them against the current page's base URL. `apiFetch` calls `fetch(path, ...)` directly — no prefix concatenation.

2. **vite.config.ts**: Added `base: process.env.VITE_APP_BASE ?? '/'` for asset URL prefix at build time. Proxy key is now `[`${VITE_APP_BASE}/api`]` with a `rewrite` that strips `VITE_APP_BASE` before forwarding to FastAPI in dev.

3. **app/api/main.py**: Added `APP_PREFIX = os.getenv("APP_PREFIX", "")` and passed `root_path=APP_PREFIX` to the `FastAPI()` constructor. This tells FastAPI its public URL prefix so OpenAPI docs generate correct server URLs.

4. **docs/nginx.md** (new): Complete reference for nginx reverse-proxy setup including location block with prefix-stripping `proxy_pass`, environment variable table, dev vs prod usage, and Docker Compose snippet.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Refactor frontend to relative paths and configure Vite base | d4cebb0 | frontend/src/api/client.ts, frontend/vite.config.ts |
| 2 | Add FastAPI root_path and create nginx docs | e139b75 | app/api/main.py, docs/nginx.md |

## Decisions Made

- **Relative paths** (`./api/...`): browser resolves against current origin + base path, so deployment at any sub-path requires no JS code changes
- **VITE_APP_BASE**: single env var controls both the Vite `base` (asset `<script src>` paths in built HTML) and the dev proxy key+rewrite
- **APP_PREFIX / root_path**: FastAPI `root_path` only affects OpenAPI docs server entries — actual route matching is unaffected; nginx strips the prefix before requests reach FastAPI
- **nginx trailing slash on proxy_pass**: `proxy_pass http://backend:8000/;` is the mechanism that strips the location prefix — documented clearly to avoid future confusion

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- `frontend/src/api/client.ts`: exists, 0 occurrences of VITE_BASE_URL, 15 relative ./api/ paths
- `frontend/vite.config.ts`: exists, VITE_APP_BASE present
- `app/api/main.py`: Python syntax valid, `root_path=APP_PREFIX` present
- `docs/nginx.md`: exists, proxy_pass example present
- Commit d4cebb0: verified in git log
- Commit e139b75: verified in git log
