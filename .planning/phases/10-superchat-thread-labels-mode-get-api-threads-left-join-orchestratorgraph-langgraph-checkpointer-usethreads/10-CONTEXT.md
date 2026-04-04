# Phase 10: SuperChat 履歴保存とモード別スレッド分離 — Context

**Gathered:** 2026-04-04 (revised)
**Status:** Ready for planning
**Source:** User design direction — revised after schema discussion

<domain>
## Phase Boundary

Chat と SuperChat をそれぞれ独立した「アプリケーション」として捉え、アプリケーション＋ユーザーという単位でスレッドを分離・管理できるようにする。

既存の `thread_labels` テーブルを廃止し、正規化されたスキーマ（`applications` / `threads` / `audit_log`）に刷新する。データ件数は少なく破棄可能なため、ALTER TABLE ではなく DROP + CREATE で移行する。

具体的には:
- `applications` テーブルを新設し、Chat / SuperChat をエンティティとして管理する
- `threads` テーブルを新設（`thread_labels` の後継）し、`app_id` FK でアプリケーションと紐付ける
- `audit_log` テーブルを新設（将来の API コスト追跡に備えたスキーマのみ。書き込みロジックは将来フェーズ）
- `GET /api/threads` を LEFT JOIN 化し、`?app_id` フィルタに対応する
- `OrchestratorGraph` を LangGraph checkpointer 対応にして SuperChat の会話継続性を実現する
- フロント `useThreads` をアプリケーション別スレッドリスト対応にする

</domain>

<decisions>
## Implementation Decisions

### スキーマ設計（確定）

```sql
-- アプリケーション登録簿
CREATE TABLE applications (
    app_id       TEXT PRIMARY KEY,          -- 'chat', 'superchat'
    display_name TEXT NOT NULL,
    enabled      BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- 初期データ
INSERT INTO applications VALUES
    ('chat',      'Chat',       true, now()),
    ('superchat', 'SuperChat',  true, now());

-- スレッドメタデータ（thread_labels の後継）
CREATE TABLE threads (
    thread_id    TEXT PRIMARY KEY,
    app_id       TEXT NOT NULL REFERENCES applications(app_id),
    github_login TEXT NOT NULL,
    label        TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);

-- 監査ログ（テーブル作成のみ。書き込みは将来フェーズ）
-- 将来の用途: Claude API 切替時のトークン使用量追跡
-- metadata 例: {"model": "claude-sonnet-4-6", "input_tokens": 1200, "output_tokens": 340}
CREATE TABLE audit_log (
    id           BIGSERIAL PRIMARY KEY,
    github_login TEXT NOT NULL,
    app_id       TEXT REFERENCES applications(app_id),
    thread_id    TEXT,                      -- SET NULL 相当（FK なし。スレッド削除後も残す）
    action       TEXT NOT NULL,             -- 'thread_created', 'message_sent', 'thread_deleted'
    metadata     JSONB,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX audit_log_github_login_idx ON audit_log(github_login);
CREATE INDEX audit_log_created_at_idx   ON audit_log(created_at);
```

### マイグレーション方針
- 既存データは少なく破棄可能 → `DROP TABLE thread_labels` → 新テーブル CREATE
- Alembic 未使用の方針を踏襲。`app/api/main.py` lifespan のインラインマイグレーションで実行

### API 変更
- `GET /api/threads` に `?app_id=chat` / `?app_id=superchat` クエリパラメータを追加
- LEFT JOIN により checkpoints が存在しないスレッドも一覧に含める
- 未指定時は全件返す（後方互換）
- `POST /api/chat` の upsert を `thread_labels` → `threads` に更新。`app_id` を記録

### フロント変更
- `useThreads(appId)` に引数を追加し、API 呼び出しに `?app_id=...` を付与
- `ChatApp` は `appId='chat'`、`SuperChatApp` は `appId='superchat'` を渡す

### OrchestratorGraph checkpointer 対応
- `build_orchestrator_graph()` に `checkpointer` 引数を追加
- `OrchestratorHandler` で `AsyncPostgresSaver` を接続し `thread_id` config を渡す

### audit_log スコープ（確定）
- **Phase 10 はテーブル作成のみ。書き込みロジックは実装しない**
- 将来 Claude API に切り替えた際にトークン課金追跡の器として使う

### Claude's Discretion
- `app_id` の型は TEXT（enum ではなく FK 参照でアプリ管理）
- `audit_log.thread_id` は TEXT（FK なし）— スレッド削除後もログを保持するため
- `GET /api/threads` の `?app_id` 未指定時は全件返す

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 現行実装（変更対象）
- `app/api/main.py` — lifespan マイグレーション・パターン（インライン ALTER/CREATE）
- `app/api/routes/chat.py` — `list_threads()`, `send_message()`, `create_thread()` の現在の実装
- `app/graph/builder.py` — LangGraph StateGraph 構成
- `app/orchestrator/graph.py` — OrchestratorGraph（checkpointer 未接続）
- `app/jobs/handlers/orchestrator_handler.py` — OrchestratorHandler の現在の実装
- `frontend/src/hooks/useThreads.ts` — スレッド CRUD フック
- `frontend/src/components/ChatApp.tsx` — Chat UI コンポーネント
- `frontend/src/components/ThreadSidebar.tsx` — スレッドサイドバー

### Phase 9 成果物（依存）
- `.planning/phases/09-*/` — SuperChat エージェント選択 UI の実装

### ADR
- `docs/adr/` — 関連 ADR

</canonical_refs>

<specifics>
## Specific Ideas

- ユーザーの指示: 「Chat/SuperChat をアプリケーションとして捉え、アプリケーション＋ユーザーという単位でチャット履歴を保存」
- 利用コンテキスト: 社内プロジェクト向け、200名規模、低トラフィック
- audit_log は将来の Claude API 切替時のコスト追跡を見据えた準備

</specifics>

<deferred>
## Deferred Ideas

- `audit_log` への書き込みロジック（将来フェーズ）
- `applications` の管理 UI（将来フェーズ）
- 第三のアプリケーション追加への対応（将来フェーズ）
- スレッドのアプリケーション間移行（対象外）

</deferred>

---

*Phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads*
*Context revised: 2026-04-04 — schema redesign (applications + threads + audit_log)*
