---
quick_id: 260513-e7g
date: 2026-05-13
type: quick
slug: dev-server-claude-worktrees
status: complete
description: dev server (uvicorn / Vite) から .claude/worktrees/ を除外
files_modified:
  - docker-compose.yml
  - frontend/vite.config.ts
---

## Summary

Phase 39 で worktree 並列実行時に dev server が `.claude/worktrees/agent-*` の大量のファイル作成・削除を watch していたため、2 種類の障害が発生していた:

1. uvicorn `--reload` のリロード暴発 (60s で 136 events) → POST `/api/threads` が 401 を返し JWT cookie が失効
2. Vite WatchFiles の transform cache 破損 → ハードリロードしても古いバンドルが配信 (AskMe ボタン消失で発覚)

両 dev server の watch 対象を狭めることで根本解決した。

## Changes

### `docker-compose.yml`

`api` service の uvicorn コマンドに `--reload-dir app` を追加。`--reload-exclude` パターン方式は fnmatch が絶対パスに弱く、ネストした worktree path に対するマッチが不安定だったため、**ホワイトリスト方式 (`--reload-dir`)** を採用。

これにより uvicorn の WatchFiles は `/app/app` 配下のみを監視し、`.claude/` `.planning/` `frontend/` `tests/` などのノイズソースは物理的に watcher の対象外になる。

### `frontend/vite.config.ts`

`server.watch.ignored` を追加し、`.claude/` `.planning/` `.git/` `node_modules/` を除外:

```ts
watch: {
  ignored: [
    '**/.claude/**',
    '**/.planning/**',
    '**/.git/**',
    '**/node_modules/**',
  ],
},
```

`.git/` と `node_modules/` は Vite default でも除外されるが、明示することで chokidar の挙動を予測可能にし、将来の Vite メジャーアップデートで default が変わってもこの quick task が想定する挙動を保つ。

## Verification

### docker-compose 反映

`docker compose restart` だけでは新しい command が反映されない (旧 config のまま再起動するため)。**`docker compose up -d` で recreate** が必要 — Plan 段階で見落としていた pitfall。

実行中 process 確認:

```
# 反映前 (restart 後):
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

# 反映後 (up -d 後):
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
```

uvicorn ログ: `Will watch for changes in these directories: ['/app/app']` ✓

### Smoke tests (実測)

| Test | 期待 | 実測 |
|------|------|------|
| api `/health/agents` | 200 | **200** ✓ |
| frontend `/orochi/` | 200 | **200** ✓ |
| Vite 起動 | ready | **ready in 200 ms** ✓ |

### Negative tests (noise should NOT trigger reload)

| Action | api WatchFiles events | frontend hmr events |
|--------|----------------------|---------------------|
| `.claude/worktrees/agent-X/test-noise/dummy.py` 作成 | **0** ✓ | **0** ✓ |
| `.claude/worktrees/agent-X/test-noise/dummy.tsx` 作成 | **0** ✓ | **0** ✓ |

### Positive tests (legitimate changes MUST still trigger reload)

| Action | api WatchFiles events | frontend hmr events |
|--------|----------------------|---------------------|
| `touch app/api/main.py` | **1** ✓ | n/a |
| `touch frontend/src/components/ChatApp.tsx` | n/a | **4** ✓ |

## Out of Scope (deferred)

- worker / mcp-server は `--reload` を使っていないため変更なし
- nginx / production 設定 (dev 専用変更)
- Vite の HMR cache 破損自体の修正 (今回はトリガー noise を抑えるのみ。HMR バグそのものは Vite v8.0.8 の既知挙動として残存。`docker compose restart frontend` で再現可能なリセット手段はある)

## Lessons Learned

1. **`docker compose restart` は古い config で再起動するため、`docker-compose.yml` の変更を反映するには `docker compose up -d` (recreate) が必要**。Plan の Task 3 verify ステップを「smoke test」だけにせず、「実行中のコマンドラインも確認」する手順を入れていれば 1 サイクルで終わっていた。
2. **uvicorn `--reload-exclude` は fnmatch 仕様で絶対パスへの再帰マッチが弱い**。ネストしたディレクトリ除外には `--reload-dir` (ホワイトリスト) のほうが頑健で意図も明確。
3. **dev server の watch noise は GSD worktree 実行で確実に再発する**。今回の修正で当該 workflow 中の barrier として機能するはず。
