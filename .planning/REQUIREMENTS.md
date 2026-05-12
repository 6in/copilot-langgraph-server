# Requirements: v6.0 UI/AI Experience

**Milestone:** v6.0 UI/AI Experience
**Status:** Active (roadmap drafted)
**Created:** 2026-04-21
**Goal:** AI からもユーザーからも扱いやすい UI 基盤を整備する — AI 操作可能性と人間 UX の両輪を強化し、ファイル I/O とバグ残債を仕上げる

---

## v6.0 Requirements

### AI-UI 操作基盤

- [ ] **AIUI-01**: 主要 UI コンポーネント（ThreadSidebar / MessageArea / MenuScreen / GemSelector / Header など）が `data-ai-role` 属性でセマンティックに識別できる
- [ ] **AIUI-02**: AI が自分の UI をチャットから操作できる MCP ツール（例: `ui_click` / `ui_read` / `ui_fill` / `ui_navigate`）が提供される
- [ ] **AIUI-03**: AI が現在表示中のページ UI 構造（どんな data-ai-role 要素があるか）を JSON で取得できる探索 API が提供される
- [ ] **AIUI-04**: AI が実行する UI 操作が observability trace（RPCContext.correlation_id 連結）に記録され、破壊的操作は確認ダイアログで人間承認を要する

### 人間向け UX 改善

- [ ] **UX-01**: ユーザーが日常のチャット操作（メッセージコピー・再送信・キャンセル・ストリーミング表示・サイドバー置換）を低摩擦で実行できる
- [ ] **UX-02**: ユーザーがスレッドとアプリを効率的に探索できる（検索・タイトル自動生成・フィルタ・最近アクセス順などで見つけやすい）
- [ ] **UX-03**: メニュー画面がダッシュボード化され、Gems/Canvas/SuperChat/DebateChat の使い分けが明瞭で初見ユーザーでも迷わない
- [ ] **UX-04**: UI がモバイル幅でも動作し、ダークモード・クロスブラウザ・chatscope バルーン幅などのデザイン破綻が解消される

### ファイル入力（チャットアップロード）

- [ ] **FIN-01**: ユーザーがチャット入力欄からテキスト・コード系ファイル（.txt/.md/.json/.csv/.py/.js 等）を添付し、LLM がコンテキストとして参照できる
- [ ] **FIN-02**: ユーザーが画像ファイル（.png/.jpg/.webp）を添付し、multimodal 対応モデルで参照できる（Copilot SDK 未対応モデルでは graceful にフォールバック）
- [ ] **FIN-03**: ユーザーが PDF / Office ファイルを添付でき、サーバー側で抽出したテキストを LLM が参照できる
- [ ] **FIN-04**: 添付ファイルが MCP ツール（execute_python / claude_code 等）からも参照できる（sandbox 内にマウントまたはパス渡し）

### ファイル出力（worker 生成 DL）

- [x] **FOUT-01**: execute_python sandbox で生成されたファイル（PDF / 画像 / CSV 等）をユーザーがチャット UI からダウンロードできる
- [x] **FOUT-02**: claude_code 実行の workspace 成果物をユーザーがチャット UI から取得できる
- [x] **FOUT-03**: 生成ファイル（画像・CSV・Markdown 等）をダウンロードせずにチャット画面上でプレビューできる
- [x] **FOUT-04**: 生成ファイルがユーザー別ストレージに保持され、過去の生成成果を一覧・再取得できる

### 既存 UI バグ潰し

- [ ] **UIFIX-01**: Mermaid View デフォルト表示時の OS レベル hang を再現・調査し、恒久的な回避策または修正を適用する
- [ ] **UIFIX-02**: CollapsibleCodeBlock のバルーン幅が chatscope の fit-content 問題で崩れる現象を解消する
- [ ] **UIFIX-03**: `tests/test_sse.py::test_sse_done_signal` の hang を修正または削除し、JobStore の dead code（register_sse/unregister_sse）を整理する
- [ ] **UIFIX-04**: 開発中に発覚する「小さな UI バグ」用に polish phase の枠を確保し、v6.0 close 前にまとめて潰す

---

## Future Requirements（v6.1+）

- RAG / ナレッジ検索（pgvector × Gem knowledge 埋め込み検索）
- エージェント管理 UI（追加・編集・削除を GUI で）
- RETRY / 回復メカニズム（DEGRADED エージェントを HEALTHY に復帰）
- 本番モード Docker Compose 整備（Vite dev server なしでビルド済み静的配信）
- Canvas アプリから MCP ツール呼び出し（FastAPI ブリッジ経由）
- 汎用 HTTP ツール（GitHub API, Slack API 等）
- エージェント別ツール allowlist（Phase 24 D-02 defer）
- MCP サーバーゲートウェイ機能（別 MCP サーバーのツール中継）
- claude_code MCP ツール認証バインド（spirit-room 方式）

---

## Out of Scope (v6.0)

- **ネイティブモバイルアプリ** — PC ブラウザ + モバイル幅レスポンシブで十分（社内 200 名、PC 主体）
- **オフライン動作** — Copilot SDK がオンライン前提、社内網常時接続が運用前提
- **ストリーミング応答（逐次トークン）** — Copilot SDK Technical Preview では未対応（v5.0 と同じく未着手）
- **AI による root 権限操作 / サーバー側システム設定変更** — UI 操作 MCP ツールはユーザーがチャット上で見える範囲に限定、OS や Docker は対象外
- **チャット以外からの UI 操作 API（外部システム連携）** — AI-UI 操作は本アプリ内部からのみ、外部 API 公開は scope 外

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| AIUI-01 | Phase 32 | active |
| AIUI-02 | Phase 33 | active |
| AIUI-03 | Phase 32 | active |
| AIUI-04 | Phase 33 | active |
| UX-01 | Phase 34 | active |
| UX-02 | Phase 34 | active |
| UX-03 | Phase 35 | active |
| UX-04 | Phase 35 | active |
| FIN-01 | Phase 36 | active |
| FIN-02 | Phase 36 | active |
| FIN-03 | Phase 37 | active |
| FIN-04 | Phase 37 | active |
| FOUT-01 | Phase 38 | active |
| FOUT-02 | Phase 38 | active |
| FOUT-03 | Phase 38 | active |
| FOUT-04 | Phase 38 | active |
| UIFIX-01 | Phase 39 | active |
| UIFIX-02 | Phase 39 | active |
| UIFIX-03 | Phase 39 | active |
| UIFIX-04 | Phase 39 | active |

**Coverage:** 20/20 v6.0 requirements mapped to phases (no orphans, no duplicates).

### Phase Distribution

| Phase | REQ-IDs | Count |
|-------|---------|-------|
| Phase 32 | AIUI-01, AIUI-03 | 2 |
| Phase 33 | AIUI-02, AIUI-04 | 2 |
| Phase 34 | UX-01, UX-02 | 2 |
| Phase 35 | UX-03, UX-04 | 2 |
| Phase 36 | FIN-01, FIN-02 | 2 |
| Phase 37 | FIN-03, FIN-04 | 2 |
| Phase 38 | FOUT-01..04 | 4 |
| Phase 39 | UIFIX-01..04 | 4 |
| **Total** | | **20** |

---

*Last updated: 2026-04-21 — v6.0 roadmap drafted (Phases 32-39, 20 REQ-IDs mapped)*
