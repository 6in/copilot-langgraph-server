# 0054. dev server の watch スコープを GSD worktree から隔離する

**Date:** 2026-05-13
**Status:** Accepted

## Context

Phase 39 で `isolation="worktree"` による並列 executor を 5 + 2 plan (Wave 1/2) 走らせた直後、dev server が 2 種類のかたちで暴発した:

1. **api (uvicorn `--reload`)** が 60 秒で 136 回のリロードイベントを発生させ、その間 POST `/api/threads` が 401 を連発。frontend が認証失敗と判断して JWT cookie を破棄し、ログイン画面に戻された。
2. **frontend (Vite WatchFiles)** は同じ noise を拾って HMR を反復起動し、内部 module graph の transform cache を破損。Phase 39 マージ後にハードリロードしても**マージ前の transform 結果**を配信し続け、`onAskMe` / `disabledReason` といった新 prop が DOM に届かない症状になった (AskMe ボタン消失で発覚)。

両者とも root cause は同じ — dev server が `.claude/worktrees/agent-*` 配下の大量の一時ファイル生成・削除を picked up していたこと。GSD orchestrator は worktree を作っては merge → 削除するため、watcher 側からは「数十のファイルが瞬時に追加・削除される」連鎖イベントとして見える。

これは GSD ワークフロー (この repo の主要な開発体験) を回すたびに再発するため、無視できない構造的問題。

## Decision

dev server 双方の watch スコープを「アプリ実体のあるディレクトリのみ」に絞る:

- **api (uvicorn)**: `--reload-dir app` を追加。`/app/app` のみ watch する**ホワイトリスト方式**に切り替え (docker-compose.yml L70-L75)。
- **frontend (Vite)**: `vite.config.ts` の `server.watch.ignored` に `**/.claude/**` `**/.planning/**` `**/.git/**` `**/node_modules/**` を追加し、明示的に**ブラックリスト方式**で除外。

worker (arq) と mcp-server は `--reload` を使っていないので変更不要。

## Alternatives Considered

### A. uvicorn `--reload-exclude` パターン方式

最初に試した案。`--reload-exclude '.claude/*'` `--reload-exclude '.planning/*'` 等を複数行で渡す。

**却下理由:** uvicorn の `--reload-exclude` は内部で `fnmatch.fnmatch(path, pattern)` を使うが、watchfiles から渡される **path は絶対パス** (`/app/.claude/worktrees/agent-X/file.py`)。Python の `fnmatch` で `.claude/*` を渡しても絶対パスの先頭にマッチしないため、深いネストの除外が**動作しない**ことを negative test で確認 (dummy file 作成で WatchFiles event が発火した)。

`*/.claude/*` や `*.claude*` といった broad パターンで救えるが、fnmatch の `*` セマンティクスを試行錯誤するより `--reload-dir` でホワイトリスト化したほうが意図も明確で頑健。

### B. `docker-compose.yml` の `volumes` から `.claude` を排除

`.:/app` bind mount を細分化して `.claude/` を mount しない方式。worktree が container 内に見えなくなるので watcher も拾わない。

**却下理由:** GSD worktree は host 側で created・destroyed されるが、host 側で watchfiles を使う場合は同じ問題が再発する。dev server 側の watch スコープを直接狭めるほうが本質的。また、`.claude/skills/` 等の MCP / agent skill 用ファイルへの read access が必要な場面が将来ありうるので、mount から外すと別の摩擦が出る可能性。

### C. 何もしない (`docker compose restart` で逃げる)

**却下理由:** GSD ワークフローを使うたびに発生する。development experience を毀損する。再発防止コストが低い (2 ファイル合計 +20 行) ので解決する。

## Consequences

### Positive

- GSD worktree 並列実行で dev server が暴発しなくなる。Negative test (`.claude/worktrees/agent-X/test.py` 作成) で api / frontend 共に 0 reload event を確認、Positive test (`app/api/main.py` / `frontend/src/components/ChatApp.tsx` touch) で正常な reload は維持。
- api 側は `app/` 配下のみ watch するため、`tests/` `scripts/` `docs/` の変更でリロードしなくなる **副次メリット** あり (テスト編集時にサーバが落ち着く、`scripts/test_mcp_tools.py` の編集で本体が再起動しないなど)。
- frontend は `.git/` `node_modules/` を明示的に ignored に含めることで、将来の Vite メジャーアップデートで default が変わっても挙動を予測可能に保つ。

### Negative / Gotchas

- **`docker compose restart` では config 変更が反映されない**。`command:` を変更したら `docker compose up -d <service>` で recreate が必要 (今回の修正中に 1 サイクル無駄にした罠)。実行中のコマンドラインは `cat /proc/<pid>/cmdline` で確認できる (slim image では `ps` が無い)。
- api 側の watch を `app/` のみに絞ったため、`mcp_server/` の編集では api はリロードしない (mcp-server コンテナ側で取り扱われる経路だから OK だが、cross-service の編集中は明示的に再起動が必要な場合あり)。
- Vite の transform cache 破損自体は **本変更では解消していない** (watch noise を抑えるだけ)。HMR cache 破損が起きた際は `docker compose restart frontend` でプロセス再起動が必要、というワークアラウンドは残る。Vite v8.0.8 の既知挙動として上流側で観察する。

### Future readers

- `--reload-dir` を増やしたくなった場合、追加ディレクトリは `app/` と同レベルで watchfiles の独立した監視対象になる。`config/` `agents/` 等を足すなら `--reload-dir <name>` を **値ごとに別オプションとして** 並べる (空白区切りではない)。
- frontend の `server.watch.ignored` は chokidar (Vite が使う) の glob 形式。`**/foo/**` で任意の深さの `foo/` 配下にマッチする。fnmatch とは別物。
- GSD orchestrator が将来 worktree を別ルート (`/.tmp` 等) に作るようになった場合、本 ADR の除外パスは更新が必要。
