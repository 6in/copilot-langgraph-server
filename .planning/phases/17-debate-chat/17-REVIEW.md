---
phase: 17-debate-chat
reviewed: 2026-04-08T10:00:00Z
depth: standard
files_reviewed: 66
files_reviewed_list:
  - app/__init__.py
  - app/api/__init__.py
  - app/api/main.py
  - app/api/models.py
  - app/api/routes/__init__.py
  - app/api/routes/agents.py
  - app/api/routes/apps.py
  - app/api/routes/auth.py
  - app/api/routes/canvas.py
  - app/api/routes/chat.py
  - app/api/routes/gems.py
  - app/api/routes/health.py
  - app/api/routes/jobs.py
  - app/api/routes/me.py
  - app/auth/__init__.py
  - app/auth/jwt_utils.py
  - app/auth/manager.py
  - app/graph/__init__.py
  - app/graph/builder.py
  - app/jobs/__init__.py
  - app/jobs/handlers/__init__.py
  - app/jobs/handlers/base.py
  - app/jobs/handlers/debate_handler.py
  - app/jobs/handlers/langgraph_handler.py
  - app/jobs/handlers/orchestrator_handler.py
  - app/jobs/job_store.py
  - app/jobs/notifier.py
  - app/jobs/worker.py
  - app/orchestrator/__init__.py
  - app/orchestrator/agent.py
  - app/orchestrator/apps.py
  - app/orchestrator/context.py
  - app/orchestrator/debate_graph.py
  - app/orchestrator/dispatcher.py
  - app/orchestrator/gem_agent.py
  - app/orchestrator/graph.py
  - app/orchestrator/script_backend.py
  - app/orchestrator/state.py
  - app/providers/__init__.py
  - app/providers/copilot.py
  - frontend/src/App.tsx
  - frontend/src/api/client.ts
  - frontend/src/components/AuthPanel.tsx
  - frontend/src/components/CanvasChatApp.tsx
  - frontend/src/components/CanvasPane.tsx
  - frontend/src/components/CanvasScreen.tsx
  - frontend/src/components/ChatApp.tsx
  - frontend/src/components/ConfirmModal.tsx
  - frontend/src/components/DebateChatApp.tsx
  - frontend/src/components/GemChatApp.tsx
  - frontend/src/components/GemSelector.tsx
  - frontend/src/components/GemsScreen.tsx
  - frontend/src/components/Header.tsx
  - frontend/src/components/MarkdownMessage.tsx
  - frontend/src/components/MenuScreen.tsx
  - frontend/src/components/MessageArea.tsx
  - frontend/src/components/SuperChatApp.tsx
  - frontend/src/components/ThreadSidebar.tsx
  - frontend/src/contexts/ThemeContext.ts
  - frontend/src/hooks/useAgents.ts
  - frontend/src/hooks/useAuth.ts
  - frontend/src/hooks/useCanvas.ts
  - frontend/src/hooks/useChat.ts
  - frontend/src/hooks/useGems.ts
  - frontend/src/hooks/useTheme.ts
  - frontend/src/hooks/useThreads.ts
  - frontend/src/main.tsx
  - frontend/src/types.ts
  - frontend/src/utils/agentColor.ts
findings:
  critical: 4
  warning: 8
  info: 6
  total: 18
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-04-08
**Depth:** standard
**Files Reviewed:** 66
**Status:** issues_found

## Summary

全システムレビュー。Python バックエンド (FastAPI + LangGraph + arq worker) および React/TypeScript フロントエンドを対象とした。
Phase 17 で追加された討論チャット機能を含む全体のセキュリティ・バグ・品質を評価した。

主な懸念事項:
- **CORS 設定**: `allow_origins` が本番向けホストを含まず、開発用 Vite サーバーのみ許可している — 本番デプロイ後に API が動作しない可能性
- **JWT blocklist**: インメモリのみで、サーバー再起動後にリボーク済みトークンが復活する — 200名規模の本番運用では許容できないリスク
- **SSE エンドポイントに認証がない**: `GET /api/chat/{job_id}/stream` は JWT チェックなしで、任意の `job_id` の結果を取得できる
- **`/api/job/{job_id}` に認証がない**: 同様に job_id を知っていれば誰でも結果を取得できる
- **`delete_thread` の ownership チェックが非致命的に無視される**: DB エラー時に `pass` してそのまま削除を続行する

---

## Critical Issues

### CR-01: SSE ストリームエンドポイントに認証がない

**File:** `app/api/routes/chat.py:139-188`

**Issue:** `GET /api/chat/{job_id}/stream` は `Depends(get_jwt_payload)` を受けていない。job_id は UUID4 で推測困難ではあるが、認証なしでアクセスできるため、job_id が漏洩した場合に他ユーザーの会話内容をストリーミング取得できる。200名規模の社内システムでは不適切。

**Fix:**
```python
@router.get("/chat/{job_id}/stream")
async def stream_job(
    job_id: str,
    request: Request,
    payload: dict = Depends(get_jwt_payload),  # 追加
):
```

---

### CR-02: ジョブステータスポーリングエンドポイントに認証がない

**File:** `app/api/routes/jobs.py:13-20`

**Issue:** `GET /api/job/{job_id}` は認証不要。job_id を知っている攻撃者が他ユーザーのチャット結果を取得できる。LangGraph の AI 出力・Canvas HTML・Gem のシステムプロンプトが含まれることがあり、情報漏洩リスクが高い。

**Fix:**
```python
@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    request: Request,
    payload: dict = Depends(get_jwt_payload),  # 追加
):
```

---

### CR-03: `delete_thread` の ownership チェックが DB エラー時に無視される

**File:** `app/api/routes/chat.py:305-313`

**Issue:** ownership チェックの `except Exception: pass` ブロックがエラー時にそのままチェックポイントの削除まで続行する。DB が一時的に使えない場合、他ユーザーのスレッドを ownership 確認なしに削除できてしまう。

```python
except Exception:
    pass  # If DB check fails, proceed with delete (non-blocking ownership check)
```

**Fix:** DB チェックが失敗した場合は 503 を返すべき。少なくともサイレントに続行させてはならない。

```python
except HTTPException:
    raise
except Exception as e:
    raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e
```

---

### CR-04: JWT blocklist がインメモリのみ — サーバー再起動でログアウト済みトークンが復活する

**File:** `app/auth/jwt_utils.py:31`

**Issue:** `_blocklist: set[str] = set()` はプロセスメモリにのみ存在する。arq worker は別プロセスで動作しており blocklist を共有していない。また、サーバー再起動でリボーク済み JWT が有効になる。ログアウト済みユーザーが同じ JWT でアクセスを継続できる。200名規模のシステムとして許容できないリスク。

**コメント:** `CLAUDE.md` に「個人ツールのため不要」とあるが、200名規模の社内システムとして開発中であることも明示されており、適切なリボーク機構が必要。

**Fix:** Redis に blocklist を移行する。既存の `redis_client` が利用可能。

```python
# jwt_utils.py に redis 依存を注入する代わりに、
# decode_jwt に redis クライアントを渡すか、
# FastAPI middleware で blocklist チェックを行う。
async def decode_jwt_with_blocklist(token: str, redis: Redis) -> dict:
    payload = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
    jti = payload.get("jti", "")
    if jti and await redis.get(f"blocklist:{jti}"):
        raise jwt.InvalidTokenError("Token revoked")
    return payload
```

---

## Warnings

### WR-01: CORS `allow_origins` が Vite dev server のみ — 本番で API が使えなくなる

**File:** `app/api/main.py:267-273`

**Issue:** `allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]` は開発用設定のみ。本番環境 (nginx + `APP_PREFIX`) から React SPA が API を呼ぶと CORS エラーになる。現在動いているなら nginx が same-origin として配信しているためだが、外部からのアクセスや別ドメイン運用で壊れる。

**Fix:** `CORS_ORIGINS` 環境変数でオーバーライドできるようにする。

```python
import json
_cors_origins_env = os.getenv("CORS_ORIGINS", "")
cors_origins = json.loads(_cors_origins_env) if _cors_origins_env else [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, ...)
```

---

### WR-02: `rename_thread` が ownership チェックなしで任意スレッドを更新できる

**File:** `app/api/routes/chat.py:316-335`

**Issue:** `PATCH /api/threads/{thread_id}` は JWT 認証があるが、`thread_id` が JWT の `github_login` に属するかどうかを確認していない。他ユーザーの `thread_id` を知っていれば `label` を変更できる。

**Fix:**
```python
async with await psycopg.AsyncConnection.connect(db_uri) as conn:
    result = await conn.execute(
        "UPDATE threads SET label = %s, updated_at = now() WHERE thread_id = %s AND github_login = %s",
        (label, thread_id, github_login),
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Thread not found")
```

---

### WR-03: `DebateChatApp` の延長処理で `handleSend` がスタックした `currentTurn` を使うリスク

**File:** `frontend/src/components/DebateChatApp.tsx:580-587`

**Issue:** `handleExtend` は `handleSend('延長')` を呼ぶ。`handleSend` はまず `createNewThread()` を呼んでしまう可能性がある（`activeThreadId` が null の場合）。討論の延長は同じスレッドで継続する必要があるが、もし `activeThreadId` が何らかの理由で null になった場合、新しいスレッドが作成されて討論状態が失われる。

```typescript
const handleExtend = () => {
    const newMaxTurns = currentTurn + extensionTurns;
    setDynamicMaxTurns(newMaxTurns);
    setDynamicCurrentTurn(currentTurn);
    setAwaitingExtension(false);
    handleSend('延長');  // activeThreadId が null の場合に新スレッド作成
};
```

**Fix:** `activeThreadId` を確認してから送信する。

```typescript
const handleExtend = () => {
    if (!activeThreadId) return; // 延長は既存スレッドが必須
    const newMaxTurns = currentTurn + extensionTurns;
    setDynamicMaxTurns(newMaxTurns);
    setDynamicCurrentTurn(currentTurn);
    setAwaitingExtension(false);
    sendMessage('延長', activeThreadId);
};
```

---

### WR-04: `useChat` の polling fallback タイマーがクリアされない (memory leak)

**File:** `frontend/src/hooks/useChat.ts:233-249`

**Issue:** `es.onerror` ハンドラで `setInterval` を作成しているが、そのタイマーの参照を保持しておらず、コンポーネントがアンマウントされてもタイマーが走り続ける。SSE エラー発生後にコンポーネントがアンマウント (例: 画面遷移) されると、タイマーが残り `setMessages` を呼び続けて警告やメモリリークを引き起こす。

```typescript
es.onerror = () => {
    es.close();
    const timer = setInterval(async () => { ... }, 2000);
    // timer をクリアする手段がない
};
```

**Fix:** `useCallback` の cleanup または `useRef` でタイマーを管理する。

```typescript
const fallbackTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

es.onerror = () => {
    es.close();
    fallbackTimerRef.current = setInterval(async () => {
        try {
            const job = await getJob(job_id);
            if (job.status === 'done' && job.result) {
                clearInterval(fallbackTimerRef.current!);
                fallbackTimerRef.current = null;
                handleResult(job.result);
                setIsThinking(false);
                await refreshThreads?.();
            }
        } catch { }
    }, 2000);
};

// useChat hook の外で cleanup
useEffect(() => {
    return () => {
        if (fallbackTimerRef.current) clearInterval(fallbackTimerRef.current);
    };
}, []);
```

---

### WR-05: `CanvasChatApp` の `initialThreadId` 処理で `setTimeout` を使ったレンダリング外の副作用

**File:** `frontend/src/components/CanvasChatApp.tsx:51-56`

**Issue:** コンポーネント本体（hooks 外）で `setTimeout(() => switchThread(initialThreadId), 0)` を直接呼んでいる。React の strict mode では render が2回呼ばれるため `setTimeout` が2回登録される。また、`useRef` フラグでガードしているが、コンポーネントのアンマウント後に `switchThread` が呼ばれる可能性がある。

```typescript
// Render 本体での副作用 — React パターン違反
if (initialThreadId && !initialSwitchDone.current) {
    initialSwitchDone.current = true;
    setTimeout(() => switchThread(initialThreadId), 0);
}
```

**Fix:** `useEffect` で処理する。

```typescript
useEffect(() => {
    if (initialThreadId) {
        switchThread(initialThreadId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
}, []); // 初回マウント時のみ
```

---

### WR-06: `app/api/main.py` の startup で DB マイグレーションと DDL が本番 `autocommit=False` 接続で走る

**File:** `app/api/main.py:53-208`

**Issue:** `psycopg.AsyncConnection.connect(DB_URI)` はデフォルトで `autocommit=False` のトランザクション内に入る。DDL (`CREATE TABLE`, `ALTER TABLE`) をトランザクション内で実行した後に `await conn.commit()` しているが、`setup()` との間でポート競合が起きた場合のロールバック処理がない。また、`CREATE INDEX CONCURRENTLY` は明示的トランザクション内では実行できないが、`CREATE INDEX` (非 CONCURRENT) はトランザクション内で動作するため今は問題なし。将来 CONCURRENT に変えた場合に壊れる。

**Fix:** 許容範囲であるが、startup ロジックを専用の Alembic マイグレーションスクリプトに分離することを推奨する。短期的には、`connect()` に `autocommit=True` を渡して DDL を個別ステートメントとして実行するか、エラー時に適切にロールバック・ログ出力する。

---

### WR-07: `_load_code_agent` が動的にロードした `agent.py` で `spec.loader` が `None` の場合に `AttributeError` が発生

**File:** `app/orchestrator/agent.py:73-77`

**Issue:** `_load_code_agent` では `spec.loader` が `None` かチェックしていない（`_check_agent_importable` は `None` チェックをしているが `_load_code_agent` はしていない）。spec が存在するが loader が None の場合、`spec.loader.exec_module(module)` で `AttributeError` になる。これは `_INIT_FAILURE_TYPES` に含まれる `AttributeError` なので `FAILED` として記録されるが、エラーメッセージが誤解を招く。

```python
def _load_code_agent(agent_dir: Path, github_token: str) -> "SubAgent":
    spec = importlib.util.spec_from_file_location(...)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # spec.loader が None の場合に AttributeError
```

**Fix:**
```python
def _load_code_agent(agent_dir: Path, github_token: str) -> "SubAgent":
    spec = importlib.util.spec_from_file_location(
        f"agent_{agent_dir.name}",
        agent_dir / "agent.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {agent_dir / 'agent.py'}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ...
```

---

### WR-08: `DebateHandler` で gem_ids の SQL プレースホルダーが手動構築されている

**File:** `app/jobs/handlers/debate_handler.py:86-94`

**Issue:** `OrchestratorHandler` は `ANY(%s::uuid[])` を使っているが、`DebateHandler` は `", ".join(["%s"] * len(gem_ids))` で動的に SQL を構築している。パラメータ値はバインドしているため SQL インジェクションの直接リスクはないが、2つのハンドラで実装が異なり、将来メンテナーが混乱する。また、`gem_ids` が空のリストの場合はこのコードパスに入らないので問題ないが、一致してほしい。

```python
placeholders = ", ".join(["%s"] * len(gem_ids))
await cur.execute(
    f"""SELECT gem_id, name, system_prompt
        FROM gems
        WHERE gem_id IN ({placeholders})
          AND (is_public = true OR github_login = %s)""",
    (*gem_ids, github_login),
)
```

**Fix:** `OrchestratorHandler` と同じパターンに統一する。

```python
await cur.execute(
    """SELECT gem_id::text, name, system_prompt
       FROM gems
       WHERE gem_id = ANY(%s::uuid[])
         AND (is_public = true OR github_login = %s)""",
    (gem_ids, github_login),
)
```

---

## Info

### IN-01: `app/api/main.py` で `import frontmatter` が関数内でインポートされている

**File:** `app/api/main.py:78`

**Issue:** `import frontmatter as fm` がリフェクション内部の `try` ブロック内に記述されている。同じ import が `app/api/main.py:229` にも再度ある。モジュールレベルでインポートするのが慣例。

**Fix:** ファイル先頭に `import frontmatter as fm` を追加し、両箇所のインライン import を削除する。

---

### IN-02: `app/api/routes/canvas.py` の `_row_to_canvas_app` に `thread_label` が返ってこない場合がある

**File:** `app/api/routes/canvas.py:43-55`

**Issue:** `get_app` エンドポイント（行 161-172）は `thread_label` を SELECT していないが、`_row_to_canvas_app` は `row.get("thread_label")` を呼んでいる。`dict_row` ファクトリを使っているためキーが存在しない場合は `None` になる（KeyError にはならない）ので実行時エラーではないが、SELECT と変換関数の不一致がバグを隠す。

**Fix:** `get_app` の SELECT にも `thread_label` (または JOIN) を追加する。

```sql
SELECT ca.app_id, ca.thread_id, ca.name, t.label AS thread_label,
       ca.html, ca.source, ca.deployed, ca.deployed_at, ca.created_at
FROM canvas_apps ca
LEFT JOIN threads t ON ca.thread_id = t.thread_id
WHERE ca.app_id = %s::uuid AND ca.github_login = %s
```

---

### IN-03: `app/jobs/handlers/langgraph_handler.py` の `github_login` が `config` に渡されているが LangGraph は使用しない

**File:** `app/jobs/handlers/langgraph_handler.py:66`

**Issue:** `config = {"configurable": {"thread_id": thread_id, "github_login": github_login}}` の `github_login` は LangGraph checkpointer が使用しないカスタムフィールド。実害はないが混乱を招く。

**Fix:** `github_login` をコメントアウトするか削除する。

---

### IN-04: `MarkdownMessage` の `code` コンポーネントで `...props` の型が広すぎる

**File:** `frontend/src/components/MarkdownMessage.tsx:242`

**Issue:** `code({ className, children, ...props }: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode })` — `...props` をインライン `<code>` に spread している。ReactMarkdown が内部的に `node` プロパティを渡すことがあり、DOM への不正なプロパティ渡しで console warning が発生する可能性がある。

**Fix:**
```typescript
code({ className, children }: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode }) {
  // ...props を削除し、必要なプロパティのみを明示的に渡す
  return <code style={...}>{children}</code>;
}
```

---

### IN-05: `useAuth` のポーリングで `flowError` が設定されないケースがある

**File:** `frontend/src/hooks/useAuth.ts:67-70`

**Issue:** Device Flow でターミナルエラー（access_denied, expired_token）が発生した場合、バックエンドは `done=false, error="..."` を返す。`doPoll` はポーリングをクリアするが、`flowError` に error メッセージをセットしていない。ユーザーには何も表示されない。

```typescript
} else if (data.error && !data.done) {
    clearInterval(pollRef.current!);
    pollRef.current = null;
    // flowError をセットしていない
}
```

**Fix:**
```typescript
} else if (data.error && !data.done) {
    clearInterval(pollRef.current!);
    pollRef.current = null;
    setFlowError(data.error);  // エラーメッセージを UI に表示
}
```

---

### IN-06: `ChatRequest` モデルに `current_turn: int = 0` のデフォルトが常に渡される

**File:** `app/api/models.py:43` と `frontend/src/hooks/useChat.ts:124-125`

**Issue:** `current_turn` は討論チャット専用フィールドだが、通常の langgraph / orchestrator タスクにも `current_turn=0` がデフォルトで arq ジョブに渡される（`worker.py:107`）。LangGraph ハンドラと Orchestrator ハンドラはこのフィールドを無視するため実害はないが、デバッグ時の混乱を招く。

**Fix:** 討論専用フィールド (`participants`, `pattern`, `max_turns`, `current_turn`) を `DebateChatRequest` のような専用モデルにサブクラス化するか、`task_type == "debate"` の場合のみ渡すようにする。

---

_Reviewed: 2026-04-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
