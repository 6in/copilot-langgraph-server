---
created: 2026-04-16T00:00:00.000Z
title: Vanilla JS 旧フロント (static/index.html + app.js + style.css) を削除
area: general
files:
  - static/index.html
  - static/app.js
  - static/style.css
  - app/api/main.py
---

## Problem

`.planning/reports/2026-04-16-cleanup-inventory.md` §1 を参照。
React 版移行後も `static/index.html` (103 行) / `static/app.js` (664 行) / `static/style.css` (779 行) が残存。`app/api/main.py:390` の `app.mount("/", StaticFiles(directory="static", html=True))` 経由で配信されているが、dev は Vite、prod は nginx が `frontend/dist/` を配信しているため実質的に死に機能。

## Solution

1. `static/index.html` / `static/app.js` / `static/style.css` を削除
2. `app/api/main.py` の catch-all `app.mount("/", ...)` を外すか、React ビルドのフォールバック用途に差し替え
3. `static/apps/` (Canvas deployed apps) と `static/js/` (iframe-rpc.js 等) は保持する — これらは個別ルートで既に配信済み
4. dev / prod 両モードで Canvas / iframe-rpc が動くことを確認
5. `frontend/src/hooks/` 内の "Mirrors static/app.js ..." コメントも現行実装を反映するように更新（任意）

影響: 旧 UI への FastAPI 直アクセスが 404 になるが、想定ユースケースはない。
