# Phase 10: SuperChat 履歴保存とモード別スレッド分離 — Context

**Gathered:** 2026-04-04
**Status:** Ready for planning
**Source:** User design direction (plan-phase invocation)

<domain>
## Phase Boundary

Chat と SuperChat をそれぞれ独立した「アプリケーション」として捉え、アプリケーション＋ユーザーという単位でスレッドを分離・管理できるようにする。

具体的には:
- `thread_labels` テーブルに `mode` カラムを追加し、スレッドがどのアプリケーション（chat / superchat）に属するかを記録する
- `GET /api/threads` を LEFT JOIN 化し、モード別にスレッドを取得できるようにする
- `OrchestratorGraph` を LangGraph checkpointer 対応にして、SuperChat でも会話継続性が機能するように修正する
- フロント `useThreads` をモード別リスト対応にして、Chat と SuperChat のスレッドを独立して管理できるようにする

</domain>

<decisions>
## Implementation Decisions

### アプリケーション概念の導入
- Chat と SuperChat をそれぞれ独立した「モード（アプリケーション）」として扱う
- スレッドは「ユーザー × モード」の組み合わせでスコープされる
- 既存の Chat スレッドは `mode=chat`、SuperChat スレッドは `mode=superchat` として区別する

### DB スキーマ変更
- `thread_labels` テーブルに `mode` カラムを追加（`VARCHAR` or enum、デフォルト `"chat"`）
- マイグレーションで既存レコードに `mode="chat"` を設定する（後方互換）

### API 変更
- `GET /api/threads` に `?mode=chat` or `?mode=superchat` のクエリパラメータを追加
- LEFT JOIN により、LangGraph checkpoints が存在しないスレッドも一覧に含まれるようにする（現状 INNER JOIN のため欠落する可能性がある）

### OrchestratorGraph の checkpointer 対応
- SuperChat 用の OrchestratorGraph が LangGraph checkpointer を正しく使えるようにする
- `thread_id` をキーとした会話継続性（メモリ保持）を修正する

### フロント useThreads の対応
- `useThreads` フックがモード別スレッドリストを管理できるよう拡張する
- ChatApp / SuperChatApp がそれぞれ自分のモードのスレッドのみ表示・操作する

### Claude's Discretion
- `mode` の型（VARCHAR / enum / check constraint）の選択
- フロントでのモード切り替え時のスレッド選択リセット挙動
- API のクエリパラメータが未指定の場合の挙動（全件 / デフォルト mode）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 現行実装
- `app/api/routes/chat.py` — スレッド一覧・チャット API の現在の実装
- `app/graph/builder.py` — LangGraph StateGraph / OrchestratorGraph の構成
- `frontend/src/hooks/useThreads.ts` — スレッド CRUD フックの現在の実装
- `frontend/src/components/ChatApp.tsx` — Chat UI コンポーネント
- `frontend/src/components/ThreadSidebar.tsx` — スレッドサイドバー

### DB / マイグレーション
- `app/db/` — データベース関連コード（マイグレーション含む）

### Phase 9 成果物（依存）
- `.planning/phases/09-*/` — Phase 9 の計画・ADR（SuperChat エージェント選択 UI の実装）

### ADR
- `docs/adr/` — 関連 ADR（特に SuperChat に関するもの）

</canonical_refs>

<specifics>
## Specific Ideas

- ユーザーの指示: 「メニューから起動されるChatやSuperChatをアプリケーションとして捕らえ、アプリケーション＋ユーザーという単位でチャット履歴を保存できるようにしてほしい」
- Chat と SuperChat は同一の画面から起動されるが、異なるグラフ・異なる用途を持つ別アプリケーションとして扱う

</specifics>

<deferred>
## Deferred Ideas

- モード追加（chat / superchat 以外の第三のモード）への対応は将来フェーズ
- スレッドのモード間移行（chat スレッドを superchat に変換など）は対象外

</deferred>

---

*Phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads*
*Context gathered: 2026-04-04 via user design direction*
