# Phase 3: Web + Chat UI - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

FastAPI バックエンド + ブラウザチャット UI の実装。
Device Flow 認証フロー（コード表示・ポーリング）、マルチターン会話表示（Markdown レンダリング）、スレッド履歴一覧付きサイドバー、モデル選択ドロップダウン、スレッドリセット機能を含む。

対象要件: AUTH-03, CHAT-01, CHAT-02, CHAT-03, CHAT-04, SESS-01, SESS-02（前倒し）

**スコープ外（このフェーズには含めない）:**
- ストリーミング応答（SDK 制約）
- モバイル対応
- セッション名付け（SESS-03）は v2

</domain>

<decisions>
## Implementation Decisions

### Auth Flow UX

- **D-01:** GitHub Device Flow の URL 表示は `window.open()` による自動オープンなし。クリック可能なリンクとして表示するのみ（ユーザーが自分で開く）。
- **D-02:** デバイスコードは Copy ボタン付きで大きく表示する（クリックでクリップボードにコピー）。
- **D-03:** 認証完了の検知はポーリング（5秒間隔）で自動検知し、完了後にページを自動更新する。ユーザーによる手動操作不要。
- **D-04:** AUTH-03（トークン期限切れ時）— ヘッダーの認証ステータス表示が "期限切れ — Click to re-auth" に変わる。バナーやモーダルは使わない。クリックで再認証フローを起動。

### Layout & Structure

- **D-05:** サイドバーあり（左側）。スレッド履歴一覧を表示する。SESS-01/02 を v1 に前倒し（AsyncSqliteSaver が既に thread_id で永続化しているため技術的に実現可能）。
- **D-06:** サイドバー上部に "New Chat" ボタンを配置する（CHAT-04）。
- **D-07:** ヘッダーは最小限: アプリ名 + 認証ステータスのみ。New Chat やコントロール類はヘッダーに入れない。
- **D-08:** メッセージバブルはユーザー右寄せ / AI 左寄せで区別する（左右分けレイアウト）。

### Model Selection

- **D-09:** ヘッダーまたはサイドバーにモデル選択ドロップダウンを配置する（配置位置は planner が決定）。
- **D-10:** モデルリストはフロントエンドにハードコード（gpt-4.1, gpt-4o, o3 など主要モデル）。バックエンドへの動的取得は行わない。
- **D-11:** モデル切り替えは次の送信から反映される（現在のスレッドにはリアルタイムで影響しない）。

### Loading State

- **D-12:** AI 応答待ち中は、チャット内の AI 側に "..." 打鍵アニメーションバブルを表示する。
- **D-13:** 送信後は入力欄と送信ボタンを無効化（重複送信を防ぐ）。応答受信後に再有効化。

### Claude's Discretion

- Markdown レンダリングライブラリの選択（marked.js + highlight.js が標準。研究者・プランナーが確認）
- FastAPI エンドポイント設計（POST /chat, GET /threads など）
- thread_id の生成・管理方法（サーバーサイドで UUID 生成が自然）
- エラー時の表示方法（メッセージリスト内にインラインエラー or トースト — Claude が判断）
- スレッドの命名表示（自動でメッセージ先頭を使うか、"Chat YYYY-MM-DD HH:mm" 形式か）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — AUTH-03, CHAT-01〜04, SESS-01, SESS-02 の受け入れ基準

### Project Context
- `.planning/PROJECT.md` — Core Value, Key Decisions, Out of Scope 一覧
- `CLAUDE.md` — 技術スタック決定（Vanilla JS, FastAPI, AsyncSqliteSaver）、制約一覧

### Existing Code (integration points)
- `app/graph/builder.py` — `build_graph(llm, checkpointer)` — FastAPI 起動時に一度コンパイルして再利用
- `app/auth/manager.py` — `CopilotAuthManager` — Device Flow + Fernet 暗号化トークン管理
- `app/providers/copilot.py` — `ChatCopilot(BaseChatModel)` — `model=` フィールドでモデル指定
- `pyproject.toml` — 現在の依存関係（fastapi/uvicorn はまだ未追加）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/graph/builder.py:build_graph(llm, checkpointer)` — コンパイル済みグラフを FastAPI lifespan で起動時に一度生成し、全リクエストで共有する。
- `app/auth/manager.py:CopilotAuthManager` — `start_device_flow()`, `poll_for_token()`, `get_token()` を FastAPI エンドポイントから呼び出す形で再利用。
- `app/providers/copilot.py:ChatCopilot` — `model` フィールドはリクエストごとに渡せる設計か、グローバルインスタンスかは研究者が確認。

### Established Patterns
- 非同期パターン: 全コードが `async def` — FastAPI の `async def` ルートと自然に統合。
- Pydantic v2 パターン: `ConfigDict` / `PrivateAttr` — FastAPI リクエスト/レスポンスモデルも同じパターンで書く。
- Checkpointer 所有権: caller-owned パターン — FastAPI lifespan で `AsyncSqliteSaver` を起動・終了管理。

### Integration Points
- FastAPI app エントリポイントが未存在 → `app/api/` または `app/main.py` として新規作成。
- 静的ファイル (HTML/CSS/JS) の配置: `static/` ディレクトリを FastAPI `StaticFiles` でマウント。
- WebSocket 不要（ストリーミングなし）— 単純な POST /chat エンドポイントで十分。

</code_context>

<specifics>
## Specific Ideas

- ポーリングは GitHub の rate limit を考慮して 5 秒間隔が適切（Device Flow 仕様の推奨値）。
- サイドバーのスレッド履歴はクリックで過去のスレッドに切り替え可能にする（AsyncSqliteSaver の thread_id を使って `ainvoke` の config を切り替える）。
- モデルドロップダウンのデフォルト値は gpt-4.1（現在の ChatCopilot デフォルトと同じ）。

</specifics>

<deferred>
## Deferred Ideas

- SESS-03（セッション名付け）— v2 要件。ユーザーがチャットに名前を付ける機能。
- ツール呼び出し（bind_tools）— v2 要件。Phase 3 のグラフ構造は既に拡張ポイント文書化済み。
- ストリーミング応答 — SDK 対応後の将来拡張。

### Reviewed Todos (not folded)

なし（Phase 3 に関連するペンディング Todo は見つからなかった）。

</deferred>

---

*Phase: 03-web-chat-ui*
*Context gathered: 2026-04-01*
