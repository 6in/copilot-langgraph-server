# Phase 10: SuperChat 履歴保存とモード別スレッド分離 - Research

**Researched:** 2026-04-04
**Domain:** PostgreSQL schema migration, LangGraph checkpointer, FastAPI route changes, React TypeScript hooks
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Chat と SuperChat をそれぞれ独立した「モード（アプリケーション）」として扱う
- スレッドは「ユーザー × モード」の組み合わせでスコープされる
- 既存の Chat スレッドは `mode=chat`、SuperChat スレッドは `mode=superchat` として区別する
- `thread_labels` テーブルに `mode` カラムを追加（`VARCHAR` or enum、デフォルト `"chat"`）
- マイグレーションで既存レコードに `mode="chat"` を設定する（後方互換）
- `GET /api/threads` に `?mode=chat` or `?mode=superchat` のクエリパラメータを追加
- LEFT JOIN により、LangGraph checkpoints が存在しないスレッドも一覧に含める
- OrchestratorGraph が LangGraph checkpointer を正しく使えるようにする
- `thread_id` をキーとした会話継続性（メモリ保持）を修正する
- `useThreads` フックがモード別スレッドリストを管理できるよう拡張する
- ChatApp / SuperChatApp がそれぞれ自分のモードのスレッドのみ表示・操作する

### Claude's Discretion
- `mode` の型（VARCHAR / enum / check constraint）の選択
- フロントでのモード切り替え時のスレッド選択リセット挙動
- API のクエリパラメータが未指定の場合の挙動（全件 / デフォルト mode）

### Deferred Ideas (OUT OF SCOPE)
- モード追加（chat / superchat 以外の第三のモード）への対応は将来フェーズ
- スレッドのモード間移行（chat スレッドを superchat に変換など）は対象外
</user_constraints>

---

## Summary

Phase 10 は三つの独立した問題を同時に解決する。(1) PostgreSQL の `thread_labels` テーブルに `mode` カラムを追加してスレッドをアプリ別に区別する、(2) `GET /api/threads` を INNER JOIN から LEFT JOIN に変更して checkpoints が存在しないスレッドも表示できるようにする、(3) `OrchestratorGraph` に LangGraph checkpointer を接続して SuperChat でも会話継続性を実現する。

現行コードの調査結果として、`thread_labels` テーブルは `app/api/main.py` の lifespan 内で `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS` のイディオムを使ってインラインマイグレーションされており、Alembic は導入されていない。同じパターンで `mode` カラムを追加できる。`GET /api/threads` は `INNER JOIN checkpoints` を使っており、checkpoints レコードがない新規スレッドがリストに出ない問題が確認できる。`OrchestratorHandler` は `build_orchestrator_graph()` を呼ぶが、`graph.compile()` に `checkpointer=` を渡しておらず、会話継続性がゼロの状態。

**Primary recommendation:** インラインマイグレーションパターンを踏襲して `mode VARCHAR NOT NULL DEFAULT 'chat'` を追加し、GET /api/threads を LEFT JOIN + `?mode` クエリパラメータ対応に変更し、OrchestratorHandler で `AsyncPostgresSaver` を checkpointer として渡す。

---

## Current State Audit (コード現状調査)

### thread_labels テーブル（実際の定義）

`app/api/main.py` lifespan より:

```python
CREATE TABLE IF NOT EXISTS thread_labels (
    thread_id  TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    github_login TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
)
```

- `mode` カラムは**存在しない**
- Alembic なし。マイグレーションは `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` でインライン実行

### GET /api/threads の現状（INNER JOIN）

`app/api/routes/chat.py` の `list_threads()`:

```sql
SELECT c.thread_id, MAX(c.checkpoint_id) as latest, tl.label, tl.updated_at
FROM checkpoints c
INNER JOIN thread_labels tl ON c.thread_id = tl.thread_id
WHERE c.checkpoint_ns = ''
  AND tl.github_login = %s
GROUP BY c.thread_id, tl.label, tl.updated_at
ORDER BY latest DESC
LIMIT 50
```

**問題:** `checkpoints` テーブルにレコードがないスレッド（作成直後・OrchestratorGraph はチェックポインタなしのため）がリストに現れない。

### OrchestratorGraph の checkpointer 未対応

`app/orchestrator/graph.py` の `build_orchestrator_graph()`:

```python
return graph.compile()   # checkpointer= 引数がない
```

`app/jobs/handlers/orchestrator_handler.py` の `handle()`:

```python
graph = build_orchestrator_graph(registry, github_token)
initial: AgentState = {"input": prompt, "output": "", "messages": [], "next": ""}
result = await graph.ainvoke(initial)
```

`thread_id` が一切使われておらず、会話ターン間で状態が保持されない。

### useThreads フック（モード非対応）

`frontend/src/hooks/useThreads.ts`:
- `listThreads()` → `GET /api/threads` を引数なしで呼ぶ
- `mode` の概念がなく、ChatApp と SuperChatApp が同じ全スレッドリストを共有している
- `createNewThread()` も mode を送らない

### POST /api/chat での mode フロー

`app/api/routes/chat.py` の `send_message()`:

```python
# Mode -> task_type translation (D-04, D-05)
task_type = "orchestrator" if body.mode == "super" else body.task_type

await arq_redis.enqueue_job("process_chat", ..., task_type=task_type, ...)

# thread_labels upsert には mode が含まれていない ← ここが問題
await conn.execute(
    "INSERT INTO thread_labels (thread_id, label, github_login) VALUES (%s, %s, %s) ON CONFLICT ...",
    (body.thread_id, label, github_login),
)
```

`body.mode` は `"simple"` | `"super"` だが、DB に保存する際のマッピングは `mode="chat"` (simple) / `mode="superchat"` (super) となる設計。

### POST /api/threads での mode

現在 `create_thread()` は UUID を返すだけで DB には書かない。mode も書かない。

```python
@router.post("/threads")
async def create_thread(payload: dict = Depends(get_jwt_payload)):
    thread_id = str(uuid.uuid4())
    label = f"Chat {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    return {"thread_id": thread_id, "label": label}
```

スレッドが DB に登録されるのは最初のメッセージ送信時（`send_message()` の upsert）。

---

## Architecture Patterns

### Pattern 1: インラインマイグレーション（プロジェクト標準）

**What:** lifespan 内で `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ADD COLUMN IF NOT EXISTS` を使う
**When to use:** Alembic 未導入のこのプロジェクト全般
**Source:** `app/api/main.py` の実装パターン（Phase 8 ADR より）

```python
# lifespan に追加する形
await conn.execute(
    "ALTER TABLE thread_labels ADD COLUMN IF NOT EXISTS mode VARCHAR NOT NULL DEFAULT 'chat'"
)
await conn.commit()
```

PostgreSQL の `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` は冪等。既存レコードに `DEFAULT 'chat'` が自動適用されるため、データマイグレーションと同時に実行できる。

### Pattern 2: LEFT JOIN でスレッドリスト

**What:** checkpoints テーブルを RIGHT 側として LEFT JOIN し、checkpoints が空でも thread_labels のレコードを返す
**When to use:** thread_labels が SSOT（Single Source of Truth）であるべき場合

```sql
SELECT tl.thread_id, MAX(c.checkpoint_id) as latest, tl.label, tl.updated_at
FROM thread_labels tl
LEFT JOIN checkpoints c ON tl.thread_id = c.thread_id AND c.checkpoint_ns = ''
WHERE tl.github_login = %s
  AND tl.mode = %s
GROUP BY tl.thread_id, tl.label, tl.updated_at
ORDER BY tl.updated_at DESC
LIMIT 50
```

注意: `ORDER BY latest DESC` から `ORDER BY tl.updated_at DESC` に変更。`latest`（checkpoint_id の MAX）は LEFT JOIN で NULL になりうる。`updated_at` は `thread_labels` に存在するので安全。

### Pattern 3: OrchestratorGraph への checkpointer 追加

**What:** `build_orchestrator_graph()` に `checkpointer` 引数を追加し、`graph.compile(checkpointer=checkpointer)` に渡す
**When to use:** LangGraph で会話継続性が必要な全グラフ

`AgentState` に `messages` フィールドが既に存在する:

```python
class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
```

`add_messages` reducer（`operator.add`）が定義されているため、checkpointer がメッセージ履歴を accumulate できる。

`OrchestratorHandler` での変更:

```python
async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    graph = build_orchestrator_graph(registry, github_token, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    initial: AgentState = {"input": prompt, "output": "", "messages": [], "next": ""}
    result = await graph.ainvoke(initial, config=config)
```

### Pattern 4: useThreads のモード別分離

**What:** `useThreads(mode)` に引数を追加し、API 呼び出しに `?mode=...` を付与する
**When to use:** 同一コンポーネントが特定モードのスレッドだけを管理する場合

```typescript
// useThreads.ts の変更
export function useThreads(mode: 'chat' | 'superchat'): UseThreadsReturn {
  const refreshThreads = useCallback(async () => {
    const data = await listThreads(mode);  // mode を渡す
    setThreads(data);
  }, [mode]);
  // ...
}
```

```typescript
// client.ts の変更
export const listThreads = (mode?: string) =>
  apiFetch<ThreadInfo[]>(`${API_BASE}/api/threads${mode ? `?mode=${encodeURIComponent(mode)}` : ''}`);
```

---

## Standard Stack

### Core (既存・変更なし)
| Library | Version | Purpose |
|---------|---------|---------|
| `psycopg` | >=3.2.0 | PostgreSQL async client (既に使用中) |
| `langgraph-checkpoint-postgres` | >=3.0.5 | AsyncPostgresSaver (既に LangGraphHandler で使用) |
| `langgraph` | >=1.1.4 | StateGraph + checkpointer API |
| React + TypeScript | 19 / 5.9 | フロント hooks |

**新規依存なし。** 既存スタックのみで全変更が実現可能。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| checkpoints での会話継続 | 独自メッセージ履歴管理 | `AsyncPostgresSaver` + `config={"configurable": {"thread_id": ...}}` | LangGraph の標準パターン。LangGraphHandler が既に証明済み |
| DB カラム追加 | データ変換スクリプト | `ALTER TABLE ADD COLUMN IF NOT EXISTS ... DEFAULT 'chat'` | PostgreSQL がデフォルト値の即時適用を保証する |
| スレッドフィルタリング | クライアント側フィルタ | SQL WHERE `tl.mode = %s` | サーバー側フィルタが正しい。全スレッドをフロントに送ってクライアントで絞るのは非効率 |

---

## Common Pitfalls

### Pitfall 1: LEFT JOIN の ORDER BY に checkpoint_id を使う
**What goes wrong:** `ORDER BY latest DESC` では、checkpoints レコードがないスレッドの `latest` が NULL になり ORDER BY が壊れる（NULL は最後になる）
**How to avoid:** `ORDER BY tl.updated_at DESC` に変更。checkpoints 未作成スレッドは `thread_labels.updated_at` で正しくソートされる

### Pitfall 2: OrchestratorGraph の AgentState が checkpointer と非互換
**What goes wrong:** `AgentState.messages` は `Annotated[list[BaseMessage], operator.add]` だが、RouterNode が `{"next": chosen}` のみ返し `messages` を返さない。チェックポインタが途中の state を保存するが次ターンで `input` が空になる
**Root cause:** `initial` に `input` を渡しているが、2ターン目の `initial` でも毎回 `input=prompt` を渡さないとルーターが前のメッセージしか見られない
**How to avoid:** `ainvoke` に毎回 `{"input": prompt, "output": "", "next": ""}` を渡す（messages は checkpointer が累積）。既存の `initial` 構造はそのままで問題ない

### Pitfall 3: POST /api/threads での mode 記録漏れ
**What goes wrong:** `create_thread()` はレコードを DB に書かない。mode は最初の `send_message()` の upsert で書かれる。この upsert に mode を追加しないと SuperChat スレッドに mode が付かない
**How to avoid:** `send_message()` の upsert SQL に `mode` カラムを追加する。`body.mode == "super"` → `'superchat'`、それ以外 → `'chat'`

### Pitfall 4: useThreads の mode 引数が既存コールサイトを壊す
**What goes wrong:** `ChatApp.tsx` と `SuperChatApp.tsx` が `useThreads()` を引数なしで呼んでいる。引数を必須にすると TypeScript エラー
**How to avoid:** 引数をオプション（デフォルト `'chat'`）にするか、両コンポーネントを同時に更新する

### Pitfall 5: mode クエリパラメータ未指定時の挙動
**What goes wrong:** 既存の GET /api/threads テストが `?mode=` なしで呼ぶ。WHERE 句に `tl.mode = %s` を追加すると既存テストが壊れる
**How to avoid:** `mode` が未指定の場合は全件返す（`WHERE tl.mode = %s` を省く）。Claude の裁量領域。既存テスト互換のためデフォルトは「全件」が安全

### Pitfall 6: thread_labels の mode 列が NULL を許容しない設計で既存レコードが INSERT 失敗
**What goes wrong:** `ALTER TABLE ADD COLUMN mode VARCHAR NOT NULL DEFAULT 'chat'` 実行後、既存 upsert が mode を渡さないと `NOT NULL` 違反
**How to avoid:** 全 INSERT/upsert 文に `mode` カラムを追加する。あるいは DEFAULT を使うため NOT NULL でも安全（DEFAULT が埋める）。INSERT ON CONFLICT の `DO UPDATE` の SET 節には mode を含めない（上書き防止）

---

## Code Examples

### DB マイグレーション（lifespan に追加）

```python
# Source: app/api/main.py の既存パターンに倣う
await conn.execute(
    "ALTER TABLE thread_labels ADD COLUMN IF NOT EXISTS mode VARCHAR NOT NULL DEFAULT 'chat'"
)
await conn.commit()
```

### GET /api/threads の LEFT JOIN + mode フィルタ

```python
# Source: 現行 list_threads() の修正案
mode_param: str | None = request.query_params.get("mode")

if mode_param:
    await cur.execute(
        """SELECT tl.thread_id, MAX(c.checkpoint_id) as latest, tl.label, tl.updated_at
           FROM thread_labels tl
           LEFT JOIN checkpoints c ON tl.thread_id = c.thread_id AND c.checkpoint_ns = ''
           WHERE tl.github_login = %s
             AND tl.mode = %s
           GROUP BY tl.thread_id, tl.label, tl.updated_at
           ORDER BY tl.updated_at DESC
           LIMIT 50""",
        (github_login, mode_param),
    )
else:
    await cur.execute(
        """SELECT tl.thread_id, MAX(c.checkpoint_id) as latest, tl.label, tl.updated_at
           FROM thread_labels tl
           LEFT JOIN checkpoints c ON tl.thread_id = c.thread_id AND c.checkpoint_ns = ''
           WHERE tl.github_login = %s
           GROUP BY tl.thread_id, tl.label, tl.updated_at
           ORDER BY tl.updated_at DESC
           LIMIT 50""",
        (github_login,),
    )
```

### POST /api/chat での mode 記録（upsert 修正）

```python
# body.mode は "simple" | "super"  →  DB の mode は "chat" | "superchat"
db_mode = "superchat" if body.mode == "super" else "chat"

await conn.execute(
    """INSERT INTO thread_labels (thread_id, label, github_login, mode)
       VALUES (%s, %s, %s, %s)
       ON CONFLICT (thread_id)
       DO UPDATE SET github_login = COALESCE(thread_labels.github_login, EXCLUDED.github_login),
                     updated_at = now()""",
    (body.thread_id, label, github_login, db_mode),
)
```

### build_orchestrator_graph への checkpointer 追加

```python
# app/orchestrator/graph.py
def build_orchestrator_graph(
    registry: SubAgentRegistry,
    github_token: str,
    checkpointer=None,
) -> Any:
    # ... (existing node/edge setup) ...
    return graph.compile(checkpointer=checkpointer)
```

```python
# app/jobs/handlers/orchestrator_handler.py
async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    graph = build_orchestrator_graph(registry, github_token, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(initial, config=config)
```

### useThreads の mode 対応

```typescript
// frontend/src/hooks/useThreads.ts
export function useThreads(mode?: 'chat' | 'superchat'): UseThreadsReturn {
  const refreshThreads = useCallback(async () => {
    try {
      const data = await listThreads(mode);
      setThreads(data);
    } catch { /* ... */ }
  }, [mode]);
  // ...
}
```

```typescript
// frontend/src/api/client.ts
export const listThreads = (mode?: string) =>
  apiFetch<ThreadInfo[]>(
    `${API_BASE}/api/threads${mode ? `?mode=${encodeURIComponent(mode)}` : ''}`
  );
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_api_chat.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| DB-01 | `thread_labels` に `mode` カラムが存在する | unit | `uv run pytest tests/test_api_chat.py -k mode -x` | ❌ Wave 0 |
| DB-02 | 既存レコードに `mode='chat'` がデフォルト設定される | manual | 実DBで `SELECT mode FROM thread_labels` 確認 | - |
| API-01 | `GET /api/threads?mode=chat` が chat スレッドのみ返す | unit | `uv run pytest tests/test_api_chat.py -k list_threads -x` | ✅ 拡張 |
| API-02 | `GET /api/threads?mode=superchat` が superchat スレッドのみ返す | unit | `uv run pytest tests/test_api_chat.py -k superchat -x` | ❌ Wave 0 |
| API-03 | checkpoints なしスレッドも LEFT JOIN で返る | unit | `uv run pytest tests/test_api_chat.py -k left_join -x` | ❌ Wave 0 |
| API-04 | POST /api/chat が正しい mode を thread_labels に保存する | unit | `uv run pytest tests/test_api_chat.py -k mode_upsert -x` | ❌ Wave 0 |
| ORC-01 | OrchestratorHandler が thread_id config で ainvoke する | unit | `uv run pytest tests/test_worker.py -k orchestrator -x` | ✅ 拡張 |
| FE-01 | useThreads(mode) が mode 付き API を呼ぶ | manual (TSC) | TypeScript build — `cd frontend && bun run build` | ✅ 変更 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_api_chat.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api_chat.py` に追加: `test_list_threads_mode_filter`, `test_list_threads_left_join`, `test_chat_upsert_mode`
- [ ] `tests/test_worker.py` に追加: `test_orchestrator_handler_uses_thread_id`

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | DB migration, LEFT JOIN, tests | ✓ (Docker) | 17 (pgvector image) | — |
| Redis | arq worker | ✓ (Docker) | 7-alpine | — |
| psycopg | DB queries | ✓ | >=3.2.0 in pyproject.toml | — |
| langgraph-checkpoint-postgres | OrchestratorHandler checkpointer | ✓ | >=3.0.5 in pyproject.toml | — |

全依存は既にインストール済み。新規インストール不要。

---

## Open Questions

1. **`GET /api/threads` でモード未指定時に全件返すか、デフォルト `chat` を返すか**
   - What we know: 既存テストは mode 引数なしで呼んでいる。全件返す方が後方互換。
   - What's unclear: SuperChatApp が起動時に全スレッドを見せたくない場合、未指定を「全件」にすると問題になる可能性
   - Recommendation: デフォルトは全件返す（後方互換）。フロントが必ず `?mode=` を渡す実装にすれば問題なし

2. **OrchestratorGraph のマルチターン会話設計**
   - What we know: AgentState には `input` フィールドがあり、毎 `ainvoke` で上書きされる。checkpointer は state 全体を保存する。
   - What's unclear: RouterNode が前ターンの `messages` を参照して routing に使うかどうかは現在の実装では使っていない
   - Recommendation: 今フェーズは「同じ thread_id で会話が継続できる（checkpointer 接続）」だけを達成すれば十分。Router の multi-turn 対応は将来フェーズでよい

3. **SuperChatApp の ThreadSidebar がスレッドを作る際の mode**
   - What we know: `createNewThread()` は POST /api/threads → UUID のみ返し、DB に書かない。最初のメッセージ送信時の upsert で mode が確定する。
   - Recommendation: 現在の遅延登録パターンを維持。`createNewThread()` に mode 引数は不要。

---

## Project Constraints (from CLAUDE.md)

- Python 3.12 / FastAPI / psycopg — 既存スタックから外れる変更は不可
- `async def` のみ — 同期 DB 操作は不可
- `arq` ワーカーパターン — handler は `TaskHandler.handle(ctx, job)` インターフェースを守る
- `thread_labels` マイグレーションは `ALTER TABLE IF NOT EXISTS` で冪等に実装する
- Alembic は未導入 — lifespan インラインマイグレーションを踏襲する
- Docker Compose が primary startup method — `docker compose up` で全変更が機能すること
- TypeScript strict mode — `useThreads` の引数追加は全コールサイトを更新する

---

## Sources

### Primary (HIGH confidence)
- `app/api/routes/chat.py` — 実際の INNER JOIN SQL、upsert パターン（直接コード調査）
- `app/api/main.py` — インラインマイグレーションパターン（直接コード調査）
- `app/orchestrator/graph.py` — checkpointer 未接続の確認（直接コード調査）
- `app/jobs/handlers/orchestrator_handler.py` — thread_id 未使用の確認（直接コード調査）
- `app/jobs/handlers/langgraph_handler.py` — AsyncPostgresSaver + config 使用例（直接コード調査）
- `frontend/src/hooks/useThreads.ts` — mode 非対応の確認（直接コード調査）
- `frontend/src/components/SuperChatApp.tsx` — `useThreads()` の呼び出し方（直接コード調査）

### Secondary (MEDIUM confidence)
- LangGraph SKILL.md — checkpointer パターン
- PostgreSQL `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ... DEFAULT` — standard SQL DDL

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 既存コード直接調査、新規依存なし
- Architecture: HIGH — LangGraphHandler が同一パターンの実証済み実装
- Pitfalls: HIGH — 実コードから直接導出（特に LEFT JOIN の NULL ソート問題と upsert の mode 漏れ）

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable project, no fast-moving dependencies)
