# Phase 18: Canvas iframe postMessage JSON-RPC API ブリッジ - Research

**Researched:** 2026-04-08
**Domain:** postMessage セキュリティ / JSON-RPC over postMessage / psycopg_pool / arq ワーカー拡張
**Confidence:** HIGH（既存コードベース直接検証 + インストール済みライブラリ確認）

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `CanvasPane.tsx` の `useEffect` 内で `window.addEventListener('message', handler)` — React コンポーネントが受信を担当
- **D-02:** 受信時に `e.origin !== window.location.origin` の場合は即座に無視（origin 検証必須）
- **D-03:** Web Worker は使用しない。React 管理下で実装し、複雑性を避ける
- **D-04:** 既存 SSE フローをそのまま流用する（POST /api/iframe-rpc → job_id → SSE → postMessage 返信）
- **D-05:** JSON-RPC の `id` フィールドでリクエストとレスポンスを対応付ける
- **D-06:** タスク識別子は `iframe_app_api`（既存 `process_chat` と同じ arq キューを使用）
- **D-07:** JSON-RPC `method` フィールドでハンドラを分岐（`QUERY` / `AI`）
- **D-08:** QUERY パラメータ: `pool_name`, `sql`, `user`
- **D-09:** SELECT 以外は拒否してエラー返却
- **D-10:** QUERY 成功フォーマット: `{"result": true, "rows": [{...}]}`
- **D-11:** QUERY エラーフォーマット: `{"result": false, "error": "メッセージ"}`
- **D-12:** AI パラメータ: `model`, `prompt`
- **D-13:** AI 成功フォーマット: `{"result": true, "responseText": "..."}`
- **D-14:** ワンショット（会話履歴なし）。ChatCopilot を直接呼び出す（LangGraph 不使用）
- **D-15:** `config/db_pools.yaml` に DSN のみ記述
- **D-16:** YAML フォーマット: `pools: { main: { dsn: ... }, analytics: { dsn: ... } }`
- **D-17:** Docker Compose で `./config/` → `/app/config/` ボリュームマウント追加
- **D-18:** `psycopg_pool.AsyncConnectionPool` を使用。ワーカー起動時に初期化
- **D-19:** 今回実装する CanvasPane（postMessage リスナー付き）で表示するアプリのみ有効
- **D-20:** 既存デプロイ済み HTML は変更しない

### Claude's Discretion

- JSON-RPC id の生成方式（UUID4 など）
- iframe 側の JavaScript ヘルパーライブラリの設計（Promise ラッパー）
- SQL SELECT 判定の実装方法（先頭キーワード判定 or sqlparse）
- psycopg_pool の最小/最大接続数デフォルト値

### Deferred Ideas (OUT OF SCOPE)

- Web API プロキシ（3番目のメソッド）— 次フェーズ
- iframe 側ヘルパーライブラリの npm パッケージ化 — 今回はインライン JS のみ
- アクセス制御（allowed_users 等）— 将来フェーズ
</user_constraints>

---

## Summary

Phase 18 は、iframe 内の Canvas HTML アプリから親フレームへ JSON-RPC メッセージを送り、
バックエンド（DB クエリ / Copilot AI）を呼び出せるブリッジを実装するフェーズ。
既存の arq + SSE フローの変更は最小限で、新規ハンドラ `IframeRpcHandler` の追加と
`POST /api/iframe-rpc` エンドポイント、`CanvasPane.tsx` への postMessage リスナー追加が主な作業。

コードベース調査の結果、既存アーキテクチャ（`TASK_HANDLERS` dict、`JobStore`、`SSE` エンドポイント）は
変更なしで再利用可能。新規ファイルは主に 3 つ（`IframeRpcHandler`、`iframe_rpc.py` ルート、
`config/db_pools.yaml`）。

**Primary recommendation:** 既存 `LangGraphHandler` のパターンをそのまま踏襲して `IframeRpcHandler` を実装する。
SQL 判定は sqlparse 不使用（未インストール）で、正規化後の先頭トークン比較で実装する。

---

## Key Findings

### 1. arq ワーカーの拡張パターン [VERIFIED: app/jobs/worker.py]

```python
# TASK_HANDLERS dict に 1 行追加するだけ
TASK_HANDLERS: dict[str, TaskHandler] = {
    "langgraph": LangGraphHandler(),
    "orchestrator": OrchestratorHandler(),
    "debate": DebateHandler(),
    "iframe_app_api": IframeRpcHandler(),  # Phase 18 追加
}
```

**重要な制約:** `process_chat` 関数シグネチャは既存のまま変更しない。
`iframe_app_api` タスクも `process_chat` キューに enqueue するが、
ハンドラが必要なフィールドのみ抽出する（`LangGraphHandler` のパターンと同じ）。

ただし、**`process_chat` の既存シグネチャには `method` と `params` フィールドが存在しない**。
`job` dict（`process_chat` が `handler.handle(ctx, job)` に渡す）に
JSON-RPC ペイロードを `rpc_method` / `rpc_params` として追加する必要がある。
または `prompt` フィールドに JSON 文字列として詰め込む方法もあるが、
型安全性のため専用フィールドが望ましい。

**推奨:** `process_chat` 関数シグネチャに `rpc_method: str | None = None` と
`rpc_params: dict | None = None` を追加し、`job` dict に含めて `IframeRpcHandler` で取り出す。

### 2. psycopg_pool.AsyncConnectionPool 初期化パターン [VERIFIED: .venv/lib/.../psycopg_pool/pool_async.py]

**インストール済みバージョン:** psycopg-pool 3.3.0 [VERIFIED: pip show]

**重要な注意点:** コンストラクタで `open=True`（デフォルト）を渡すと RuntimeWarning が出る。
正しい非同期初期化パターンは以下の通り:

```python
# arq startup hook の中で（イベントループが存在する状態）
pool = AsyncConnectionPool(conninfo=dsn, open=False, min_size=1, max_size=5)
await pool.open(wait=True, timeout=30.0)
ctx["db_pools"][pool_name] = pool
```

または context manager として使う:

```python
async with AsyncConnectionPool(conninfo=dsn, min_size=1, max_size=5) as pool:
    ...  # ここで使う
```

**ワーカーの startup/shutdown hook でのライフサイクル管理:**
arq の `on_startup` と `on_shutdown` は非同期関数なので、
pool を `open=False` で作成し、startup で `await pool.open(wait=True)` を呼び、
shutdown で `await pool.close()` を呼ぶパターンが正しい。

**接続の使い方:**
```python
async with pool.connection() as conn:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
# context manager を抜けると自動的に pool に返却 + commit/rollback
```

**デフォルト値の推奨:**
- `min_size=1`（ワーカーは通常 1 タスク/プロセス）
- `max_size=5`（複数並行タスクに対応、社内規模 200 名向けで十分）

### 3. SQL SELECT 判定（sqlparse 未インストール） [VERIFIED: pip show sqlparse → not installed]

`sqlparse` は pyproject.toml に含まれておらず、未インストール。
SELECT 判定は Python 標準ライブラリのみで実装する。

**推奨実装（堅牢な正規化アプローチ）:**

```python
import re

_ALLOWED_PREFIXES = frozenset(["SELECT", "WITH"])
# SQL コメント除去 + 先頭トークン取得
_COMMENT_RE = re.compile(r'/\*.*?\*/|--[^\n]*', re.DOTALL)

def is_select_only(sql: str) -> bool:
    """SELECT または WITH から始まるクエリのみ許可する。
    
    単純な先頭キーワード判定。複数文（;区切り）は不許可。
    """
    cleaned = _COMMENT_RE.sub('', sql).strip()
    if ';' in cleaned.rstrip(';'):
        # セミコロンが途中にある = 複数文 → 拒否
        actual = cleaned.rstrip(';')
        if ';' in actual:
            return False
    first_token = cleaned.split()[0].upper() if cleaned.split() else ''
    return first_token in _ALLOWED_PREFIXES
```

**既知の制限（プランナーへの注記）:**
- コメント内の `SELECT` で始まる偽装クエリは上記で防げる
- `WITH ... DELETE` (CTE + 書き込み) は `WITH` を許可するため通過してしまう
- この制限はセキュリティ要件と照らし合わせて判断が必要。
  DB ユーザーを読み取り専用ロールに制限することで二重防御とするのが確実。

**より安全な実装（推奨追加）:** `db_pools.yaml` の DSN に読み取り専用ユーザーを使用することを
YAML コメントに明記する。コードは `is_select_only` で第 1 防御、DB 権限で第 2 防御とする。

### 4. CanvasPane.tsx への postMessage リスナー追加 [VERIFIED: frontend/src/components/CanvasPane.tsx]

現在の `CanvasPane.tsx`（321 行）には postMessage 関連コードは一切ない。
`sandbox="allow-scripts allow-forms"` のみ（`allow-same-origin` なし）。

**重要な制約:** `allow-same-origin` がないため、iframe 内の JS から `parent.postMessage()` は
使えるが、iframe が同一オリジンとして扱われない。これは設計通り（XSS 防止、D-03）。

**追加する useEffect パターン:**

```typescript
const iframeRef = useRef<HTMLIFrameElement>(null);

useEffect(() => {
  const handler = async (e: MessageEvent) => {
    // D-02: origin 検証（必須）
    if (e.origin !== window.location.origin) return;
    
    // JSON-RPC 形式チェック
    const msg = e.data;
    if (!msg || typeof msg !== 'object' || msg.jsonrpc !== '2.0') return;
    
    const { id, method, params } = msg;
    if (!id || !method) return;
    
    // POST /api/iframe-rpc へ転送
    const resp = await apiFetch('./api/iframe-rpc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, method, params }),
    });
    const { job_id } = await resp.json();
    
    // SSE で完了待ち（既存 GET /api/job/{id}/stream を流用）
    // ... SSE 処理 ...
    
    // 結果を iframe に返信
    iframeRef.current?.contentWindow?.postMessage(
      { jsonrpc: '2.0', id, result: jobResult },
      window.location.origin  // targetOrigin は '*' ではなく origin を指定
    );
  };
  
  window.addEventListener('message', handler);
  return () => window.removeEventListener('message', handler);
}, []);
```

**targetOrigin の注意:** iframe → parent は origin が異なるが、
parent → iframe への返信は `'*'` または iframe の srcDoc の場合 `'*'` を使う必要がある
（srcDoc の iframe は `null` オリジン）。CONTEXT.md D-02 は受信の origin 検証であり、
**返信の targetOrigin は `'*'` が正しい**（srcDoc iframe は `null` origin なので
`window.location.origin` を指定すると届かない）。

### 5. POST /api/iframe-rpc エンドポイントパターン [VERIFIED: app/api/routes/chat.py]

`POST /api/chat` エンドポイントとほぼ同じ構造で実装できる。
`arq_redis.enqueue_job("process_chat", ...)` のパターンを流用する。

**注意点:** `iframe-rpc` エンドポイントは JWT 認証が必要（親フレームが認証済みユーザー）。
iframe 内 HTML は直接 JWT を持たないため、**親フレームの React コンポーネントが
認証済みの状態で `POST /api/iframe-rpc` を呼び出す**設計になっている（D-04 の流れ）。

### 6. JobStore / SSE の変更不要 [VERIFIED: app/jobs/job_store.py, app/api/routes/jobs.py]

- `JobStore.save_result()` / `notify()` は変更なしで使用可能
- `GET /api/job/{id}/stream` SSE エンドポイントは変更なしで使用可能
- `GET /api/job/{id}` ポーリングエンドポイントも変更なしで使用可能

`IframeRpcHandler.handle()` は `LangGraphHandler` と同じパターンで:
1. 処理実行
2. `job_store.save_result(job_id, json.dumps(result_dict))` — JSON 文字列として保存
3. `notifier.done()` で SSE 通知

### 7. docker-compose.yml のボリュームマウント追加 [VERIFIED: docker-compose.yml]

現在の `api` と `worker` サービスはともに `.:/app` マウントを持つ。
`./config/` ディレクトリはリポジトリルートに作成するだけで `/app/config/` として
コンテナ内からアクセス可能（追加マウント不要）。

ただし **D-17 では明示的な `./config/` → `/app/config/` マウントを追加**するよう決定されている。
`.:/app` マウントで既にカバーされているが、意図を明示するために個別マウントを追加するのも可。
プランナーへの注記: **追加マウントは不要だが、YAML に明示したい場合は追加してもよい**。

---

## Architecture Decision

### 新規ファイル一覧

| ファイル | 役割 |
|---------|------|
| `app/jobs/handlers/iframe_rpc_handler.py` | `IframeRpcHandler(TaskHandler)` — QUERY/AI 処理 + DB プール管理 |
| `app/api/routes/iframe_rpc.py` | `POST /api/iframe-rpc` エンドポイント |
| `config/db_pools.yaml` | pool_name → DSN マッピング |

### 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `app/jobs/worker.py` | `TASK_HANDLERS` に `"iframe_app_api": IframeRpcHandler()` を追加、startup/shutdown に pool 初期化/終了を追加 |
| `app/jobs/worker.py` | `process_chat` シグネチャに `rpc_method`, `rpc_params` フィールドを追加 |
| `app/api/main.py` | `iframe_rpc.router` を `include_router` に追加 |
| `frontend/src/components/CanvasPane.tsx` | `useEffect` + `useRef` で postMessage リスナー追加 |
| `docker-compose.yml` | `./config:/app/config` マウント追加（api/worker サービス） |

### データフロー

```
iframe JS
  └─ parent.postMessage({jsonrpc:'2.0', id:'...', method:'QUERY', params:{...}})

CanvasPane.tsx (useEffect handler)
  ├─ origin 検証 (e.origin !== window.location.origin → 無視)
  ├─ POST /api/iframe-rpc {id, method, params}  [JWT cookie 付き]
  ├─ job_id 受け取り
  ├─ GET /api/job/{job_id}/stream (SSE)
  │    └─ status: 'done' を受信
  ├─ GET /api/job/{job_id} で result 取得
  └─ iframe.contentWindow.postMessage({jsonrpc:'2.0', id, result}, '*')

POST /api/iframe-rpc (FastAPI)
  └─ arq_redis.enqueue_job("process_chat", task_type="iframe_app_api", rpc_method=..., rpc_params=...)

arq worker (process_chat → IframeRpcHandler.handle)
  ├─ method == 'QUERY'
  │    ├─ is_select_only(sql) 検証
  │    ├─ ctx["db_pools"][pool_name] から接続取得
  │    ├─ SELECT 実行 → rows を list[dict] に変換
  │    └─ job_store.save_result(job_id, json.dumps({"result": true, "rows": rows}))
  └─ method == 'AI'
       ├─ ChatCopilot(github_token=..., model=model)
       ├─ ainvoke([HumanMessage(prompt)])
       └─ job_store.save_result(job_id, json.dumps({"result": true, "responseText": text}))
```

---

## Implementation Approach

### Wave 0: 設定・インフラ準備

1. `config/db_pools.yaml` を作成（プレースホルダー DSN で）
2. `docker-compose.yml` に `./config:/app/config:ro` マウント追加（api/worker）
3. `config/` を `.gitignore` に追加（DSN に認証情報含むため）

### Wave 1: バックエンド

1. `app/jobs/handlers/iframe_rpc_handler.py` に `IframeRpcHandler` 実装
   - `startup_pools(ctx, config_path)` ユーティリティ関数（worker.py から呼ぶ）
   - `handle(ctx, job)` — QUERY/AI 分岐
   - SELECT 判定ロジック（`is_select_only`）

2. `app/jobs/worker.py` を更新
   - `TASK_HANDLERS` に追加
   - `startup` hook に pool 初期化を追加
   - `shutdown` hook に pool close を追加
   - `process_chat` シグネチャに `rpc_method`, `rpc_params` を追加

3. `app/api/routes/iframe_rpc.py` に `POST /api/iframe-rpc` を実装

4. `app/api/main.py` に router を追加

### Wave 2: フロントエンド

1. `CanvasPane.tsx` に postMessage リスナーを追加
   - `useRef<HTMLIFrameElement>` を preview `<iframe>` に紐付け
   - `useEffect` で `window.addEventListener('message', handler)`
   - SSE ポーリングロジック（既存 `useChat` の SSE 処理を参考に）

---

## Common Pitfalls

### Pitfall 1: AsyncConnectionPool の非同期初期化
**何が起きるか:** `AsyncConnectionPool(dsn, open=True)` をコンストラクタで呼ぶと
RuntimeWarning（および将来的にエラー）が発生する。イベントループがコンストラクタ時点で
確立していない場合、内部の asyncio オブジェクト生成が壊れる。
**回避策:** `open=False` で作成し、`await pool.open(wait=True)` を arq startup hook 内で呼ぶ。

### Pitfall 2: `process_chat` シグネチャへの追加フィールド
**何が起きるか:** arq は job 関数のパラメータ名でペイロードをマッピングする。
`rpc_method` / `rpc_params` を追加しないと enqueue_job で渡しても受け取れない。
**回避策:** デフォルト値付き（`rpc_method: str | None = None`）で追加し後方互換性を保つ。

### Pitfall 3: iframe → parent postMessage の origin
**何が起きるか:** `sandbox="allow-scripts"` のみで `allow-same-origin` なしの iframe は
`null` オリジンになる。親が `e.origin !== window.location.origin` でフィルタすると、
`null` origin（文字列 `"null"`）のメッセージを弾いてしまう。
**回避策:** `srcDoc` を使った iframe は `e.origin === 'null'`（文字列）になる。
D-02 の判定を `e.origin !== window.location.origin && e.origin !== 'null'` とするか、
または whitelist 方式（`e.origin === window.location.origin || e.origin === 'null'`）に変更する。
ただし CONTEXT.md D-02 は厳格な検証を求めているため、`null` origin を許可するかは
**プランナーが確認する必要がある設計判断**。

> **重要:** デプロイ済みアプリ（`/apps/{app_id}/`）は StaticFiles から配信されるので
> `window.location.origin` と同じオリジンになる。`srcDoc` プレビューのみ `null` origin。
> Preview tab でもリスナーを機能させたいなら `null` 許可が必要。

### Pitfall 4: `pool.connection()` は commit/rollback を自動実行
**何が起きるか:** `async with pool.connection() as conn:` は context manager 終了時に
自動で commit（正常時）または rollback（例外時）を行う。
SELECT-only なら問題ないが、将来的に INSERT が混入した場合に自動 commit される。
**回避策:** 読み取り専用用途として明示し、将来の書き込み追加時は注意喚起コメントを残す。

### Pitfall 5: SSE ループでの iframe への返信タイミング
**何が起きるか:** CanvasPane が複数の RPC リクエストを同時送信した場合、
SSE ストリームが混在する（job_id で区別されているので実際には問題ないが）。
複数の `useEffect` 内の async handler が並行実行される。
**回避策:** 各リクエストは独立した job_id を持ち、SSE エンドポイントも job_id 単位なので
問題は発生しないが、テストで並行送信を確認する。

### Pitfall 6: GitHub token の取得
**何が起きるか:** `IframeRpcHandler` の AI メソッドは `ChatCopilot(github_token=...)` を
必要とするが、`process_chat` の `github_token` フィールドは JWT から復号されたトークン。
`POST /api/iframe-rpc` エンドポイントは `get_github_token` dependency を使って
JWT から復号して enqueue する（`POST /api/chat` と同じパターン）。
**回避策:** `iframe_rpc.py` で `github_token: str = Depends(get_github_token)` を使う（確認済みパターン）。

### Pitfall 7: CTE (WITH) + 書き込み
**何が起きるか:** `WITH cte AS (...) DELETE FROM ...` のような CTE + 書き込みは
`is_select_only` の先頭トークン `WITH` チェックをすり抜ける。
**回避策:** DB ユーザーを読み取り専用ロールに制限（第 2 防御として必須）。
YAML コメントにその旨を明記する。

---

## Validation Architecture

`.planning/config.json` 未確認だが、`nyquist_validation` 設定を想定して含める。

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements → Test Map

| 要件 | テスト種別 | ファイル | コマンド |
|------|-----------|---------|---------|
| `is_select_only` — SELECT 許可 / 非 SELECT 拒否 | unit | `tests/test_iframe_rpc_handler.py` | `pytest tests/test_iframe_rpc_handler.py -x` |
| QUERY ハンドラ — SELECT 実行・rows 返却 | unit (mock pool) | `tests/test_iframe_rpc_handler.py` | 同上 |
| AI ハンドラ — ChatCopilot ワンショット | unit (mock ChatCopilot) | `tests/test_iframe_rpc_handler.py` | 同上 |
| `POST /api/iframe-rpc` — enqueue 成功 | unit (mock arq_redis) | `tests/test_iframe_rpc_route.py` | `pytest tests/test_iframe_rpc_route.py -x` |
| `POST /api/iframe-rpc` — 未認証 401 | unit | `tests/test_iframe_rpc_route.py` | 同上 |

### Wave 0 Gaps

- [ ] `tests/test_iframe_rpc_handler.py` — IframeRpcHandler の unit テスト
- [ ] `tests/test_iframe_rpc_route.py` — POST /api/iframe-rpc のルートテスト

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | JWT cookie (既存 `get_jwt_payload` dependency) |
| V4 Access Control | yes | 親フレームのみが `/api/iframe-rpc` を呼べる（JWT 必須） |
| V5 Input Validation | yes | `is_select_only()` + DB ロール制限 |
| V6 Cryptography | no | 追加の暗号化なし |

### Known Threat Patterns

| パターン | STRIDE | 標準緩和策 |
|---------|--------|-----------|
| SQL インジェクション | Tampering | psycopg パラメータバインディング（`%s`）を必須とする。文字列フォーマットで SQL 組み立て禁止 |
| クロスオリジン postMessage 偽装 | Spoofing | `e.origin` 検証（D-02）|
| 任意コード実行（非 SELECT クエリ） | Tampering | `is_select_only()` + 読み取り専用 DB ユーザー（二重防御）|
| DB プール名インジェクション | Tampering | `db_pools` dict の `pool_name` は YAML からロードしたキーのみ許可（`if pool_name not in ctx["db_pools"]: error`） |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| psycopg-pool | IframeRpcHandler (QUERY) | yes | 3.3.0 | — |
| pyyaml | db_pools.yaml 読み込み | yes | pyproject.toml に含む | — |
| arq | ワーカー | yes | pyproject.toml に含む | — |
| sqlparse | SQL 判定 | no | — | 正規表現 + 先頭トークン判定で代替 |

---

## Code Examples

### AsyncConnectionPool 初期化（arq startup hook）

```python
# app/jobs/worker.py

import yaml
from psycopg_pool import AsyncConnectionPool

DB_POOLS_CONFIG = os.getenv("DB_POOLS_CONFIG", "/app/config/db_pools.yaml")

async def startup(ctx: dict) -> None:
    ctx["redis_client"] = Redis.from_url(REDIS_URL)
    ctx["job_store"] = JobStore(ctx["redis_client"])
    
    # DB プール初期化
    ctx["db_pools"] = {}
    try:
        with open(DB_POOLS_CONFIG) as f:
            pools_cfg = yaml.safe_load(f)
        for name, cfg in pools_cfg.get("pools", {}).items():
            pool = AsyncConnectionPool(conninfo=cfg["dsn"], open=False, min_size=1, max_size=5)
            await pool.open(wait=True, timeout=30.0)
            ctx["db_pools"][name] = pool
    except FileNotFoundError:
        pass  # 設定ファイルなし — QUERY メソッドは使用不可

    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        await checkpointer.setup()


async def shutdown(ctx: dict) -> None:
    await ctx["redis_client"].aclose()
    for pool in ctx.get("db_pools", {}).values():
        await pool.close()
```

### IframeRpcHandler の骨格

```python
# app/jobs/handlers/iframe_rpc_handler.py

import json
import re
from psycopg.rows import dict_row
from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.providers.copilot import ChatCopilot
from langchain_core.messages import HumanMessage

_COMMENT_RE = re.compile(r'/\*.*?\*/|--[^\n]*', re.DOTALL)
_ALLOWED_PREFIXES = frozenset(["SELECT", "WITH"])

def is_select_only(sql: str) -> bool:
    cleaned = _COMMENT_RE.sub('', sql).strip()
    body = cleaned.rstrip(';')
    if ';' in body:
        return False  # 複数文
    tokens = body.split()
    return bool(tokens) and tokens[0].upper() in _ALLOWED_PREFIXES


class IframeRpcHandler(TaskHandler):
    async def handle(self, ctx: dict, job: dict) -> dict:
        job_id = job["job_id"]
        reply_to = job["reply_to"]
        method = job.get("rpc_method", "")
        params = job.get("rpc_params") or {}

        job_store = ctx["job_store"]
        notifier = build_notifier(reply_to, job_store)

        try:
            if method == "QUERY":
                result = await self._handle_query(ctx, params)
            elif method == "AI":
                result = await self._handle_ai(job, params)
            else:
                result = {"result": False, "error": f"Unknown method: {method}"}
            
            await job_store.save_result(job_id, json.dumps(result))
            await notifier.done()
        except Exception as e:
            await job_store.save_result(job_id, json.dumps({"result": False, "error": str(e)}))
            await notifier.done()
        
        return {"job_id": job_id, "status": "done"}

    async def _handle_query(self, ctx: dict, params: dict) -> dict:
        pool_name = params.get("pool_name", "")
        sql = params.get("sql", "")
        
        if not is_select_only(sql):
            return {"result": False, "error": "Only SELECT queries are allowed"}
        
        db_pools = ctx.get("db_pools", {})
        if pool_name not in db_pools:
            return {"result": False, "error": f"Unknown pool: {pool_name}"}
        
        pool = db_pools[pool_name]
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql)  # パラメータバインディング注意: sql は静的のみ
                rows = await cur.fetchall()
        
        return {"result": True, "rows": [dict(r) for r in rows]}

    async def _handle_ai(self, job: dict, params: dict) -> dict:
        model = params.get("model", "claude-sonnet-4.5")
        prompt = params.get("prompt", "")
        github_token = job.get("github_token", "")
        
        llm = ChatCopilot(github_token=github_token, model=model)
        try:
            result = await llm.ainvoke([HumanMessage(content=prompt)])
            text = result.content
            return {"result": True, "responseText": text}
        finally:
            await llm.close()
```

### iframe 側 JavaScript ヘルパー（Claude's Discretion で設計）

Canvas HTML アプリに埋め込む Promise ラッパー。
UUID は `crypto.randomUUID()` を使用（モダンブラウザでサポート済み）。

```javascript
// iframe 側 HTML に埋め込む <script>
const _rpc_pending = new Map();
window.addEventListener('message', (e) => {
  const { id, result, error } = e.data || {};
  if (!id) return;
  const pending = _rpc_pending.get(id);
  if (!pending) return;
  _rpc_pending.delete(id);
  if (error) pending.reject(new Error(error));
  else pending.resolve(result);
});

function rpc(method, params, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const id = crypto.randomUUID();
    const timer = setTimeout(() => {
      _rpc_pending.delete(id);
      reject(new Error('RPC timeout'));
    }, timeout);
    _rpc_pending.set(id, {
      resolve: (r) => { clearTimeout(timer); resolve(r); },
      reject:  (e) => { clearTimeout(timer); reject(e); },
    });
    parent.postMessage({ jsonrpc: '2.0', id, method, params }, '*');
  });
}

// 使用例
// const { rows } = await rpc('QUERY', { pool_name: 'main', sql: 'SELECT * FROM items', user: 'app' });
// const { responseText } = await rpc('AI', { model: 'claude-sonnet-4.5', prompt: 'Hello' });
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `srcDoc` iframe の `e.origin` は文字列 `'null'` になる | Pitfall 3 | 実装した postMessage リスナーが Preview tab で動作しない |
| A2 | arq の `on_startup` は実行時に asyncio イベントループが確立済み | Key Finding 2 | `await pool.open()` が失敗する |
| A3 | `/apps/{app_id}/` でホストされるデプロイ済みアプリは同一オリジン | Key Finding 4 | origin 検証が厳しすぎてデプロイ済みアプリからの RPC が届かない |

---

## Open Questions

1. **Preview tab（srcDoc）の postMessage origin**
   - 現状: `srcDoc` の iframe は `null` origin になると想定
   - 確認が必要: Preview tab でも postMessage ブリッジを機能させるか？機能させないなら D-02 のままで OK
   - 推奨: プランナーがユーザーに確認するか、実装時に動作テストで確認する

2. **`WITH ... DELETE` (CTE + 書き込み) の扱い**
   - `WITH` で始まるクエリを許可すると書き込み CTE をすり抜ける
   - DB ユーザーを読み取り専用ロールに制限することで実害を防げるが、
     `db_pools.yaml` のコメントにその旨を明記する必要がある

3. **`process_chat` シグネチャ変更の影響範囲**
   - `rpc_method` / `rpc_params` を追加してもデフォルト `None` なので後方互換
   - 既存のすべての `enqueue_job("process_chat", ...)` 呼び出しに影響なし（確認済み）

---

## Sources

### Primary (HIGH confidence — コードベース直接検証)
- `app/jobs/worker.py` — TASK_HANDLERS パターン、process_chat シグネチャ
- `app/jobs/job_store.py` — JobStore API（save_result / notify / get）
- `app/api/routes/chat.py` — enqueue_job パターン、get_jwt_payload / get_github_token
- `app/api/routes/jobs.py` — SSE エンドポイント実装
- `app/api/routes/canvas.py` — Canvas API パターン（psycopg 接続、JWT 保護）
- `frontend/src/components/CanvasPane.tsx` — 現在の iframe sandbox 設定
- `app/providers/copilot.py` — ChatCopilot API（ainvoke、close）
- `docker-compose.yml` — 現在のボリュームマウント設定
- `.venv/lib/python3.12/site-packages/psycopg_pool/pool_async.py` — AsyncConnectionPool 実装（v3.3.0）
- `pyproject.toml` — インストール済み依存関係（psycopg-pool, pyyaml, sqlparse なし）

### Secondary (MEDIUM confidence)
- `docs/pre/iframe_app_enhanced.md` — Phase 18 の原案仕様
- `.planning/phases/18-canvas-iframe-postmessage-json-rpc-api/18-CONTEXT.md` — 確定済み設計決定

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — インストール済みライブラリを直接確認
- Architecture: HIGH — 既存コードを直接検証してパターンを確認
- Pitfalls: HIGH — コード調査で発見した具体的な落とし穴

**Research date:** 2026-04-08
**Valid until:** 2026-05-08（安定したライブラリ構成のため 30 日）
