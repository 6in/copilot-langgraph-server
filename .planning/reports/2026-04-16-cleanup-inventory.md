# 棚卸しレポート — 未参照コード / サンプル / 旧実装

**作成日:** 2026-04-16
**対象リポジトリ:** copilot-langgraph (main branch)
**関連 todo:** `.planning/todos/completed/2026-04-15-cleanup-unused-sources-and-samples.md`

実行ツール:
- Python: `vulture` (`uvx --from vulture`) に対して `app/` + `mcp_server/server.py` + `mcp_server/tools/`
- Frontend: `knip` (`bunx knip`) — 未使用 export・未宣言 deps 検出
- 手作業 rg によるファイル参照確認

## サマリ

| カテゴリ | 件数 | 影響 | 優先度 |
|----------|------|------|--------|
| Vanilla JS 旧フロント (static/) | 3 ファイル 1,546 行 | 中 | 高 |
| `super-agent-sample/` 独立サンプル | 214 MB | 低 | 中 |
| vulture 80%+ Python 未使用 | 4 件 | 小 | 中 |
| knip 未使用 frontend export | 7 件 | 小 | 中 |
| frontend 未使用依存 (`rehype-highlight`) | 1 件 | 小 | 中 |
| scripts/ ワンショット群 | 5 ファイル | 不明 | 低 |

**結論:** 削除によるサイズ・認知負荷低減は明確。ただし一括削除は危険なので、以下の follow-up todo に分割する（`.planning/todos/pending/2026-04-16-cleanup-*.md` 参照）。

---

## 1. Vanilla JS 旧フロント (`static/index.html`, `static/app.js`, `static/style.css`)

- `static/index.html` (103 行) — 旧 UI のページ
- `static/app.js` (664 行) — 旧 UI のロジック。認証・チャット送受信・スレッド管理すべてを含む
- `static/style.css` (779 行) — 旧 UI のスタイル

**状態:** React 版への移行後も `app/api/main.py:390` で `app.mount("/", StaticFiles(directory="static", html=True))` としてマウントされており、FastAPI 直アクセス（例: `http://localhost:8000/`）では旧 UI が配信される。しかし:

- dev mode では Vite dev server (`:5173`) が主、`:8000` 直アクセスは使われていない
- prod mode では nginx が `frontend/dist/` を `/react` プレフィックスで配信、`static/*` は Canvas apps / iframe-rpc JS の配信にしか使われていない
- `frontend/src/hooks/useAuth.ts`・`useChat.ts`・`useThreads.ts` 等に「Mirrors static/app.js ...」という参照コメントが残っており、コピー元としてのみ残されている

**影響範囲:**
- `static/apps/` (Canvas deployed apps) — 保持必須
- `static/js/iframe-rpc.js`・`static/js/parent-bridge.js` — Canvas の iframe で読み込まれる（保持必須）

**推奨アクション:** `static/index.html`・`static/app.js`・`static/style.css` の 3 ファイルを削除し、`app.mount("/", ...)` の行も縮退。`/js/`・`/apps/` は個別ルートで既に配信されているので、catch-all ルートを撤去しても副作用はない見込み（ただし要動作確認）。

---

## 2. `super-agent-sample/` 独立サンプル

- サイズ: **214 MB**（`.venv` 含む）
- 最終アクティブコミット: 2026-04 初旬の Phase 8 関連
- 内容: 独立した pyproject + 旧 SubAgent プロトタイプ

**状態:** 本体の `app/orchestrator/` 配下に実装が移り、Phase 8 以降は参照されていない。ただし ADR・Plan ドキュメントからは旧実装としての参照が多数残る可能性あり。

**推奨アクション:**
- 内容を `.planning/archive/super-agent-sample/` へ移動（または完全削除）
- `.venv/` だけでも先に削除（214 MB のうち大半が venv）
- git 履歴は `git log super-agent-sample` で追える

---

## 3. vulture 検出（80%+ confidence）

```
app/api/routes/chat.py:25: unused import 'ChatResponse' (90%)
app/providers/copilot.py:30: unused import 'Runnable' (90%)
app/providers/copilot.py:266: unused variable 'tool_choice' (100%)
mcp_server/server.py:25: unused variable 'server' (100%)
```

**判定:**
- `ChatResponse` import: Pydantic モデルの再エクスポート目的の可能性あり — 要確認
- `Runnable` import: 型注釈のみ使用の可能性 — 要確認
- `tool_choice`: `bind_tools()` の `tool_choice` パラメータを受け取って捨てている可能性 — 要確認
- `server` 変数: FastMCP lifespan シグネチャ要件の false positive（`async def lifespan(server)` で受け取るが使わない）

**推奨アクション:** 3 件は実コードの確認の上で削除 / 型注釈化、`mcp_server/server.py` の false positive は無視。

---

## 4. knip 検出（frontend）

**未使用依存:**
- `rehype-highlight` — package.json に残っているが MarkdownMessage は Monaco で描画しており不要

**未宣言依存（peer のみ）:**
- `monaco-editor` — `@monaco-editor/react` の peer として必要。意図通り（package.json に追加しなくても動くが、明示する方が保守的）

**未使用 export:**
- `src/api/client.ts`: `getThreadMessages`, `getCanvasApp`, `postIframeRpc`
- `src/api/client.ts`: `IframeRpcResponse` (type)
- `src/hooks/useAuth.ts`: `AuthState` (type)
- `src/utils/markdownTable.ts`: `AG_GRID_THRESHOLD_ROWS`, `AG_GRID_THRESHOLD_COLS`（今回追加、内部定数として export しているだけ）

**推奨アクション:**
- `rehype-highlight` を `bun remove rehype-highlight` で削除
- `client.ts` の未使用 function / type は削除
- `AG_GRID_THRESHOLD_*` は export を剥がして内部 const に戻す（または将来のテスト用として維持）

---

## 5. `scripts/` ワンショット

| ファイル | 用途 | 現役？ |
|----------|------|--------|
| `chat_test.py` | 手動チャットテスト | 不明 — 動作確認用の古いスクリプト疑いあり |
| `generate_adr_index.py` | ADR INDEX 自動生成 | 現役（pre-commit hook） |
| `install-hooks.sh` | hook インストーラ | 現役（README 参照） |
| `lint_tools.py` | MCP ツール lint | 不明 |
| `probe_sdk_events.py` | Copilot SDK イベント調査 | 調査スクリプト — 調査完了なら削除候補 |
| `test_mcp_tools.py` | MCP ツール疎通テスト | 不明 |
| `validate_graph.py` | Graph 検証 | 不明 |

**推奨アクション:** 各スクリプトに「最終目的」「現役/廃止」のコメントヘッダを追加するか、`scripts/archive/` へ移動。

---

## 6. その他の気づき

- `docs/test-iframe-rpc.js` / `docs/test-iframe-rpc-prompt.md` が `docs/` 直下に置かれている — `docs/archi/` 等に整理すべき
- `.planning/debug/resolved/` にある解決済みデバッグログが累積している（今回の範囲外だが `/gsd-cleanup` 対象）
- `docs/pre/` の phase1_spec.md 等は、現行の phase 構成が進んだ後の整合性が要確認

---

## Follow-up todos（削除 PR 用に分割）

本レポート時点で **新規作成予定** の todo（別コミットで追加）:

1. `2026-04-16-remove-legacy-vanilla-js-frontend.md` — static/index.html + app.js + style.css の削除と mount ルート縮退
2. `2026-04-16-archive-super-agent-sample.md` — super-agent-sample/ の `.planning/archive/` への移動
3. `2026-04-16-prune-frontend-unused-exports-and-deps.md` — knip 指摘の export / rehype-highlight 削除
4. `2026-04-16-resolve-vulture-python-warnings.md` — vulture 80%+ の Python 警告対応

これらを `/gsd-check-todos` で 1 件ずつ処理すれば、各削除を小さな PR にできる。

---

## 実行コマンド（再現用）

```bash
# Python
docker compose exec -T worker uvx --from vulture vulture \
  app/ mcp_server/server.py mcp_server/tools/ \
  --exclude '*/.venv/*,*/__pycache__/*' --min-confidence 80

# Frontend
docker compose exec -T frontend bunx knip --no-progress

# 参照検索
ls -la static/ super-agent-sample/ scripts/
du -sh super-agent-sample/
```
