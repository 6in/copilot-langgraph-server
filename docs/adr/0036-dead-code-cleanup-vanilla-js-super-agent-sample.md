# 0036. デッドコード一括クリーンアップ（旧 Vanilla JS フロント・super-agent-sample・未使用 export）

**Date:** 2026-04-16  
**Status:** Accepted

## Context

プロジェクトが React 19 + TypeScript + Vite のフロントエンドと Python バックエンドの構成に成熟した一方で、以下のデッドコードが蓄積していた:

1. **`static/index.html` + `app.js` + `style.css`** (1,546 行) — Phase 7 で React 版に移行した後も `app.mount("/", StaticFiles(..., html=True))` で配信され続けていた旧 Vanilla JS フロントエンド。
2. **`super-agent-sample/`** (19 ファイル, 2,161 行 + 214MB .venv) — Phase 8 時代の独立プロトタイプ。`app/orchestrator/` に実装が移行しており、Phase 9 以降は参照なし。
3. **Frontend 未使用 export / 依存** — `rehype-highlight` (Monaco で不要)、`getCanvasApp`・`postIframeRpc`・`IframeRpcResponse` (Canvas は postMessage ブリッジ経由)、`AuthState` (内部型として十分)。
4. **Python 未使用 import / 変数** — vulture 80%+ confidence の 4 件 (`ChatResponse` import、`Runnable` import、`tool_choice` 変数、`server` lifespan 引数)。

棚卸しレポート (`.planning/reports/2026-04-16-cleanup-inventory.md`) で全容を把握し、影響範囲を特定した上で実施。

## Decision

4 カテゴリを 1 ブランチ (`chore/cleanup-batch-2026-04-16`) で一括削除する。

- `static/index.html`・`app.js`・`style.css` を削除し、`app.mount("/", StaticFiles(..., html=False))` に変更。`static/apps/` (Canvas) と `static/js/` (iframe-rpc) は保持。
- `super-agent-sample/` を完全削除（git 履歴で追跡可能）。
- Frontend: `bun remove rehype-highlight`、未使用 export を削除 or `export` を剥がし内部化。
- Python: 未使用 import 削除、`tool_choice` → `_tool_choice` リネーム、`server` → `_server` リネーム。
- フロントの旧 static 参照コメント ("Mirrors static/app.js ...") を現行の説明に更新。

## Alternatives Considered

1. **段階的 PR 分割** — 4 件をそれぞれ別 PR にする案。しかし全て「削除のみ・ロジック変更なし」なので 1 ブランチの方が効率的。CI でまとめて動作確認できる。
2. **super-agent-sample をアーカイブディレクトリに移動** — `.planning/archive/` へ移す案。214MB の .venv を含むため git 履歴のサイズ問題は解決せず、完全削除の方がクリーン。
3. **static/ の catch-all mount 自体を削除** — `apps/` と `js/` が `/apps` と `/js/{filename}` の個別ルートで配信済みなので mount 不要にも見えるが、将来の静的ファイル追加に備えて `html=False` で残す方が柔軟。

## Consequences

**ポジティブ:**
- コードベースから **3,735 行** 削減。`super-agent-sample/.venv/` (214MB) がディスクからも消える。
- `vulture --min-confidence 80` の出力がゼロに。`knip` の指摘が `monaco-editor` (peer dep, 意図通り) のみに。
- 新規メンバーが旧 Vanilla JS とサンプルに惑わされなくなる。

**ネガティブ / 注意点:**
- `http://localhost:8000/` (FastAPI 直アクセス) が 404 になる。開発は Vite dev server (`:5173`) 経由なので影響なし。
- `postIframeRpc` を削除したが、Canvas アプリが `call()` で任意 MCP ツールを呼ぶ機能は `IframeRpcHandler` に未実装のまま。別 todo で対応予定。
- `super-agent-sample/` の git 履歴は残るが、過去コミットで large blob (.venv が track されていた場合) があるかは未検証。`git gc` やリポジトリサイズ削減が必要な場合は `git filter-branch` 等を検討。
