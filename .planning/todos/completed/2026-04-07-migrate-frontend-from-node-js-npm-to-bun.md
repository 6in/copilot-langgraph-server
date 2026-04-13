---
created: 2026-04-07T15:26:41.240Z
title: Migrate frontend from Node.js/npm to Bun
area: ui
files:
  - frontend/Dockerfile
  - frontend/package-lock.json
  - docker-compose.yml
---

## Problem

CLAUDE.md には「Docker サービスでは Bun を使う」と記載されているが、実際は Node.js 22 + npm で動いている。
- `frontend/Dockerfile`: `node:22-alpine` イメージ、`npm install`、`npm run dev`
- `frontend/package-lock.json` が存在（bun.lock はなし）
- `docker-compose.yml`: `node_modules` を anonymous volume でマウント

CLAUDE.md の記述が実態と乖離している。

## Solution

1. `frontend/Dockerfile` を `oven/bun` イメージに変更し、`npm install` → `bun install`、CMD を `bun run dev` に変更
2. `frontend/package-lock.json` を削除し、`bun install` で `bun.lock` を生成
3. `docker-compose.yml` の `node_modules` anonymous volume はそのまま維持（bun も node_modules に出力する）
4. ローカル開発でも `npm` → `bun` に統一するか判断する
5. `@types/node` の代わりに `@types/bun` を追加するか検討（必須ではない）
6. CLAUDE.md の技術スタック記述を実態に合わせて更新

Vite 8 は Bun と互換あり。`package.json` の変更は不要。
