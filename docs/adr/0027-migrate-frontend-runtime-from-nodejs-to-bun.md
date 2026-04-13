# 0027. フロントエンドランタイムを Node.js/npm から Bun に移行

**Date:** 2026-04-14  
**Status:** Accepted

## Context

CLAUDE.md の技術スタックには「フロントエンドのパッケージマネージャー: Bun（Docker）」と記載されていたが、実際の `frontend/Dockerfile` は `node:22-alpine` イメージ上で `npm install` / `npm run dev` を実行する構成になっていた。

具体的な乖離:
- dev ステージ: `FROM node:22-alpine`、`RUN npm install`、`CMD ["npm", "run", "dev"]`
- `frontend/package-lock.json` が存在（4,700行超）
- builder ステージのみ `oven/bun:1-alpine` を使用しており、dev/builder で異なるランタイムが混在していた

## Decision

`frontend/Dockerfile` の dev ステージを `oven/bun:1-alpine` に統一し、npm コマンドをすべて bun に置き換えた。

変更内容:
- `FROM node:22-alpine AS dev` → `FROM oven/bun:1-alpine AS dev`
- `RUN npm install` → `RUN bun install`
- `CMD ["npm", "run", "dev", ...]` → `CMD ["bun", "run", "dev", ...]`
- `COPY package*.json` → `COPY package.json bun.lock* bun.lockb*`（builder ステージも同様に統一）
- `frontend/package-lock.json` を削除

## Alternatives Considered

**Node.js/npm を維持してドキュメントを修正する:** CLAUDE.md の記述を実態に合わせる方向。ただし builder ステージがすでに Bun を使用しており、dev/prod で異なるランタイムを使うことに合理性がないため不採用。

**ローカル開発環境にも Bun をインストールする:** コンテナ外での `bun install` に対応するかを検討したが、開発は基本的に `docker compose up` 経由のため現時点では不要と判断。

## Consequences

**ポジティブ:**
- dev / builder ステージでランタイムが統一され、CLAUDE.md の記述と実態が一致した
- `package-lock.json`（4,718行）が消え、リポジトリが軽量化された
- Vite と Bun の互換性は問題なく、`docker compose up` での動作確認済み

**注意点:**
- 初回ビルド時に `bun install` が実行され `bun.lock` が生成される。ロックファイルをコミットしていないため `--frozen-lockfile` は現状機能しない。将来的には以下でロックファイルを取得してコミットすること:
  ```bash
  docker compose run --rm frontend cat /app/bun.lock > frontend/bun.lock
  git add frontend/bun.lock && git commit -m "chore(frontend): add bun.lock"
  ```
- `bun.lockb`（バイナリ形式）と `bun.lock`（テキスト形式）はバージョンによって異なるため、`COPY` パターンは両方を含む `bun.lock* bun.lockb*` としている。
