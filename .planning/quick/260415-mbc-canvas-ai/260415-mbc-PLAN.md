---
phase: quick-260415-mbc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/jobs/handlers/iframe_rpc_handler.py
  - static/js/iframe-rpc.js
  - tests/jobs/handlers/test_iframe_rpc_handler_ai.py
autonomous: true
requirements:
  - CANVAS-AI-MODEL-01
user_setup: []

must_haves:
  truths:
    - "Canvas アプリの iframe JS から ai(prompt) をモデル指定なしで呼ぶと Haiku 相当のモデルで応答が返る（現在の sonnet 既定から変更）"
    - "Canvas アプリの iframe JS から ai(prompt, { model: 'sonnet' }) のようにエイリアスで呼び出すとサーバー側で claude-sonnet-4-6 に解決されて実行される"
    - "ai(prompt, { model: 'claude-sonnet-4-6' }) のように実モデル ID 直指定でも動作する（既存の Copilot モデル ID がそのまま通る）"
    - "存在しないエイリアス（例: 'turbo'）や空文字列の model を指定した場合、サーバーは silent fallback せず {result: false, error: '...'} を返す"
    - "既存の Canvas アプリ（iframe-rpc.js の ai() を再ダウンロードしていない）は model パラメータなしでも引き続き動作し、Haiku で応答が返る（後方互換）"
  artifacts:
    - path: "app/jobs/handlers/iframe_rpc_handler.py"
      provides: "AI モデルエイリアス解決 + 検証ロジック + Haiku デフォルト"
      contains: "MODEL_ALIASES"
    - path: "static/js/iframe-rpc.js"
      provides: "ai(prompt, opts?) 第2引数でモデル指定"
      contains: "model"
    - path: "tests/jobs/handlers/test_iframe_rpc_handler_ai.py"
      provides: "_handle_ai のモデル解決とエラーハンドリングのユニットテスト"
      contains: "test_handle_ai_"
  key_links:
    - from: "static/js/iframe-rpc.js ai()"
      to: "iframe_rpc_handler._handle_ai"
      via: "postMessage -> /api/iframe-rpc -> arq job rpc_params.model"
      pattern: "rpc_params"
---

<objective>
Canvas アプリ（iframe でホストされるユーザー定義 HTML アプリ）から `iframe-rpc.js` の `ai()` ヘルパー経由で呼び出される AI リクエストに、モデル指定機能を追加する。

**確定した実装パス (プランナー調査結果):**

1. **経路:** Canvas の AI 呼び出しは `IframeRpcHandler._handle_ai`（`task_type='iframe_app_api'` / `method='AI'`）を通る。Todo が挙げていた `langgraph_handler.py` は通常チャット経路で、Canvas iframe RPC とは無関係。
2. **現状:** `iframe_rpc_handler.py:123` で既に `params.get("model", "claude-sonnet-4.5")` を読んでいる。つまりプロトコル層の受け口はあるが、(a) クライアント `iframe-rpc.js` の `ai()` が model を送る口を持たない、(b) デフォルトが Sonnet であり Todo 方針の Haiku ではない、(c) エイリアス解決がない、(d) 無効値を silent に Copilot SDK へ流してしまう。
3. **`apps.py` について:** `app/orchestrator/apps.py` は AppRegistry（menus や superchat のシステムパッケージ）用で、ユーザーが作る Canvas HTML アプリ（`canvas_apps` DB テーブル）とは別物。Canvas HTML アプリにアプリ単位のモデル設定を永続化するには `canvas_apps` テーブルにカラム追加が必要だが、Canvas アプリは HTML 単体で自己完結しており、AI モデル指定は HTML 内の JS から毎回渡すのが自然。→ **今回の quick タスクでは DB スキーマ変更は行わず、リクエスト毎の `model` パラメータのみで実装する。** アプリ単位デフォルトは Deferred として末尾に切り出す。
4. **エイリアス解決:** Copilot SDK は `claude-haiku-4-5-20251001` / `claude-sonnet-4-6` / `gpt-4.1` を実 ID として既に受けている（`app/orchestrator/graph.py`, `gem_agent.py` で確認済み）。3 エイリアス（haiku/sonnet/gpt-4.1）を Python dict でハードコードマッピングする方針を採用する。追加モデル拡張は将来 `config.yaml` 管理に移行する余地を残す。

**Purpose:** Canvas アプリ開発者が用途に応じてコスト/速度/精度を選べるようにする。既定を Haiku にすることで、想定ユーザー規模 200 名での Copilot コスト消費も抑える。

**Output:** `iframe-rpc.js` の `ai()` が `opts.model` を受け取り、サーバー側で検証付きエイリアス解決 → ChatCopilot に実モデル ID を注入。既存 Canvas アプリは無変更で Haiku 既定に自動移行（後方互換）。
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/todos/pending/2026-04-15-canvas-app-ai-request-model-selection.md
@app/jobs/handlers/iframe_rpc_handler.py
@app/providers/copilot.py
@static/js/iframe-rpc.js

<interfaces>
<!-- 実装済みコードから抽出した契約。実行者は探索不要。 -->

**ChatCopilot (app/providers/copilot.py):**
```python
class ChatCopilot(BaseChatModel):
    model: str = "gpt-4.1"               # Copilot SDK create_session(model=...) にそのまま渡される
    github_token: Optional[str] = None
    # 使い方: ChatCopilot(github_token=token, model=resolved_model_id)
    # async def close() で CopilotClient subprocess を停止
```

**IframeRpcHandler._handle_ai (現状 — 変更前):**
```python
async def _handle_ai(self, job: dict, params: dict) -> dict:
    model = params.get("model", "claude-sonnet-4.5")   # ← 問題: sonnet デフォルト、検証なし
    prompt = params.get("prompt", "")
    github_token = job.get("github_token", "")
    llm = ChatCopilot(github_token=github_token, model=model)
    try:
        result = await llm.ainvoke([HumanMessage(content=prompt)])
        return {"result": True, "responseText": result.content}
    finally:
        await llm.close()
```

**iframe-rpc.js ai() (現状 — 変更前):**
```js
export function ai(prompt, timeoutMs = 60000) {
  return _call('AI', { prompt }, timeoutMs);
}
```

**既存の実 Copilot モデル ID（リポジトリ内使用実績あり）:**
- `claude-haiku-4-5-20251001` — `app/orchestrator/graph.py:33` (Router 用軽量モデル)
- `claude-sonnet-4-6` — `app/orchestrator/gem_agent.py:9`, `agent.py`, `tool_agent.py`
- `gpt-4.1` — `app/providers/copilot.py:59` (ChatCopilot 既定)

**注:** `iframe_rpc_handler.py:123` と `langgraph_handler.py:52` の既存 `claude-sonnet-4.5` は実在しない ID の可能性が高いが、本 quick の範囲外。`langgraph_handler.py` 側は今回触らない。
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: サーバー側 — エイリアス解決 + 検証 + Haiku デフォルト</name>
  <files>
    app/jobs/handlers/iframe_rpc_handler.py,
    tests/jobs/handlers/test_iframe_rpc_handler_ai.py
  </files>
  <behavior>
    - Test 1 (default): `params = {"prompt": "hi"}` (model 未指定) → 解決後モデルが `claude-haiku-4-5-20251001` になる。ChatCopilot はモック。
    - Test 2 (alias): `params = {"prompt": "hi", "model": "sonnet"}` → 解決後モデルが `claude-sonnet-4-6`。
    - Test 3 (alias haiku): `params = {"prompt": "hi", "model": "haiku"}` → `claude-haiku-4-5-20251001`。
    - Test 4 (alias gpt): `params = {"prompt": "hi", "model": "gpt-4.1"}` → `gpt-4.1`（エイリアス兼実 ID）。
    - Test 5 (direct ID passthrough): `params = {"prompt": "hi", "model": "claude-sonnet-4-6"}` → そのまま `claude-sonnet-4-6`（ホワイトリスト済み実 ID は素通り）。
    - Test 6 (invalid): `params = {"prompt": "hi", "model": "turbo"}` → `{"result": false, "error": "..."}` を返す。ChatCopilot は呼ばれない（`llm.ainvoke` が呼ばれていないことを assert）。エラーメッセージには許可された値一覧を含むこと。
    - Test 7 (empty string): `params = {"prompt": "hi", "model": ""}` → 無効として拒否（Test 6 と同等のエラー）。None 明示指定時は既定(Haiku)にフォールバック（空文字と None を区別する）。
    - Test 8 (backward compat): `_handle_ai` が従来通り `{"result": True, "responseText": ...}` を返すこと（正常系の契約は不変）。
  </behavior>
  <action>
    1. `app/jobs/handlers/iframe_rpc_handler.py` を編集:
       - モジュールトップに以下を追加（クラス外定数）:
         ```python
         # AI モデルエイリアス → Copilot SDK の実モデル ID へのマッピング。
         # 将来 config.yaml に移行する余地を残すためクラス外の定数として定義する。
         MODEL_ALIASES: dict[str, str] = {
             "haiku": "claude-haiku-4-5-20251001",
             "sonnet": "claude-sonnet-4-6",
             "gpt-4.1": "gpt-4.1",
         }
         # 許可済み実モデル ID（エイリアスを使わず直接指定された場合のホワイトリスト）
         ALLOWED_MODEL_IDS: frozenset[str] = frozenset(MODEL_ALIASES.values())
         DEFAULT_MODEL_ALIAS: str = "haiku"

         def resolve_model(value: str | None) -> str:
             """None は既定(haiku)に解決。エイリアスは実 ID に解決。実 ID 直指定は
             ALLOWED_MODEL_IDS にあれば素通り。それ以外（未知のエイリアス、空文字列、
             ALLOWED 外の実 ID）は ValueError を投げる。silent fallback は行わない。"""
             if value is None:
                 return MODEL_ALIASES[DEFAULT_MODEL_ALIAS]
             if value == "":
                 raise ValueError(
                     f"model must not be empty. Allowed aliases: {sorted(MODEL_ALIASES.keys())}, "
                     f"or one of the real IDs: {sorted(ALLOWED_MODEL_IDS)}"
                 )
             if value in MODEL_ALIASES:
                 return MODEL_ALIASES[value]
             if value in ALLOWED_MODEL_IDS:
                 return value
             raise ValueError(
                 f"Unknown model '{value}'. Allowed aliases: {sorted(MODEL_ALIASES.keys())}, "
                 f"or one of the real IDs: {sorted(ALLOWED_MODEL_IDS)}"
             )
         ```
       - `_handle_ai` を書き換え:
         - `raw_model = params.get("model")` で生値を取得（`.get(..., default)` のデフォルトは使わない — None と未指定を同一扱いしたいため）。
         - `try: model = resolve_model(raw_model) except ValueError as e: return {"result": False, "error": str(e)}` を ChatCopilot インスタンス化より前に入れる。
         - その後は従来どおり `llm = ChatCopilot(github_token=github_token, model=model)` → `ainvoke` → `{"result": True, "responseText": ...}`。
         - 既存の try/finally の構造は維持する。
    2. `tests/jobs/handlers/test_iframe_rpc_handler_ai.py` を新規作成:
       - `pytest` + `unittest.mock.patch` で `app.jobs.handlers.iframe_rpc_handler.ChatCopilot` をモック。
       - `AsyncMock()` で `ainvoke` と `close` を await 可能にする。
       - `IframeRpcHandler()._handle_ai(job={...}, params={...})` を直接 await するテスト群を Behavior 節の通り 8 本書く。
       - Test 6/7 では `ChatCopilot` が一度も呼ばれていない（`mock_cls.assert_not_called()`）ことを assert。
       - ファイルヘッダにこのタスクで追加したことが分かる docstring を入れる。
    3. 既存の他テストを壊していないことの確認用コマンドは Verify 節参照。

    **注意:** 現状コードの `claude-sonnet-4.5`（実在しない可能性が高い）は本タスクの範囲外。`resolve_model` の導入によりこの誤った既定値は置き換わる。`langgraph_handler.py` 側の同名問題は今回触らない。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph &amp;&amp; docker compose exec -T api uv run pytest tests/jobs/handlers/test_iframe_rpc_handler_ai.py -x -q</automated>
  </verify>
  <done>
    - `MODEL_ALIASES` / `ALLOWED_MODEL_IDS` / `resolve_model` が `iframe_rpc_handler.py` に追加されている
    - `_handle_ai` が `resolve_model` を使いモデル解決前に ChatCopilot を生成しない
    - 8 テストすべてパス
    - 無効モデルが silent fallback せず `{"result": false, "error": ...}` を返す
    - デフォルトが Haiku に変わっている（Test 1 で確認）
  </done>
</task>

<task type="auto">
  <name>Task 2: クライアント側 — iframe-rpc.js ai() 第2引数でモデル指定 + 手動スモーク</name>
  <files>static/js/iframe-rpc.js</files>
  <action>
    1. `static/js/iframe-rpc.js` の `ai()` を以下のシグネチャに変更:
       ```js
       /**
        * Call the parent AI endpoint.
        * @param {string} prompt
        * @param {object} [opts] - optional options
        * @param {string} [opts.model] - model alias ('haiku'|'sonnet'|'gpt-4.1') or full Copilot model ID.
        *   If omitted, the server defaults to Haiku (low-cost, fast).
        *   Unknown values are rejected with {result:false, error:...} — no silent fallback.
        * @param {number} [opts.timeoutMs=60000]
        * @returns {Promise<{result: true, responseText: string}>}
        */
       export function ai(prompt, opts = {}) {
         const { model, timeoutMs = 60000 } = opts || {};
         const params = { prompt };
         if (model !== undefined) params.model = model;
         return _call('AI', params, timeoutMs);
       }
       ```
    2. **後方互換の保持（重要）:** 既存 Canvas HTML アプリは `ai('hello', 30000)` のように第2引数に数値を渡している可能性がある。これを検出して旧シグネチャ互換として扱う:
       ```js
       export function ai(prompt, optsOrTimeout) {
         let model, timeoutMs = 60000;
         if (typeof optsOrTimeout === 'number') {
           timeoutMs = optsOrTimeout;  // legacy: ai(prompt, 30000)
         } else if (optsOrTimeout && typeof optsOrTimeout === 'object') {
           model = optsOrTimeout.model;
           if (typeof optsOrTimeout.timeoutMs === 'number') timeoutMs = optsOrTimeout.timeoutMs;
         }
         const params = { prompt };
         if (model !== undefined) params.model = model;
         return _call('AI', params, timeoutMs);
       }
       ```
    3. ファイル先頭の使用例コメントに `await ai('Hello', { model: 'sonnet' })` の例を追記。
    4. `parent-bridge.js` は RPC params をそのまま転送しているため変更不要（確認のみ）。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph &amp;&amp; node -e "const fs=require('fs');const s=fs.readFileSync('static/js/iframe-rpc.js','utf8');if(!/opts\.model|optsOrTimeout/.test(s))throw new Error('model param not wired');if(!/typeof optsOrTimeout === 'number'/.test(s))throw new Error('legacy number compat missing');console.log('ai() signature OK');"</automated>
  </verify>
  <done>
    - `iframe-rpc.js` の `ai()` が `opts.model` を受け取り `_call('AI', {prompt, model?}, timeoutMs)` に渡している
    - 旧シグネチャ `ai(prompt, 30000)`（数値第2引数）が引き続き動作する
    - JSDoc にモデル指定のドキュメントが追加されている
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Canvas アプリでの手動動作確認</name>
  <what-built>
    - サーバー: `_handle_ai` のモデル解決（Haiku 既定 + エイリアス + 検証）
    - クライアント: `ai(prompt, { model })` API
  </what-built>
  <how-to-verify>
    1. `docker compose up -d` でサービス起動。`curl -s http://127.0.0.1:9222/json/version` で Chromium デバッグポートを確認（未起動ならユーザーに `! chromium --remote-debugging-port=9222 --no-first-run --no-default-browser-check &` を依頼）。
    2. ブラウザで `http://localhost:5173/orochi/` を開き、Device Flow でログイン。
    3. Canvas 画面へ移動し、以下の HTML を持つアプリを新規作成してデプロイ（または既存の Canvas アプリの HTML を編集）:
       ```html
       <!DOCTYPE html>
       <html><body>
       <button id="b1">Haiku (default)</button>
       <button id="b2">Sonnet (alias)</button>
       <button id="b3">Invalid model</button>
       <pre id="out"></pre>
       <script type="module">
         import { ai } from '$URL_PREFIX/js/iframe-rpc.js';
         const out = document.getElementById('out');
         document.getElementById('b1').onclick = async () => {
           out.textContent = 'haiku...';
           out.textContent = JSON.stringify(await ai('say hi in 5 words'), null, 2);
         };
         document.getElementById('b2').onclick = async () => {
           out.textContent = 'sonnet...';
           out.textContent = JSON.stringify(await ai('say hi in 5 words', { model: 'sonnet' }), null, 2);
         };
         document.getElementById('b3').onclick = async () => {
           out.textContent = 'invalid...';
           out.textContent = JSON.stringify(await ai('hi', { model: 'turbo' }), null, 2);
         };
       </script>
       </body></html>
       ```
    4. 期待結果:
       - ボタン 1 (default): `{result: true, responseText: "..."}` が返る。サーバーログで `model=claude-haiku-4-5-20251001` が使われていることを確認（iframe_rpc_handler に一時的な logger.info を追加するか、chrome devtools Network タブで確認）。
       - ボタン 2 (sonnet alias): 同じく `{result: true, responseText: "..."}` が返る。ログで `claude-sonnet-4-6`。
       - ボタン 3 (invalid): `{result: false, error: "Unknown model 'turbo'. Allowed aliases: ..."}` が返る。
    5. **後方互換確認:** 既にデプロイ済みの Canvas アプリが 1 つあれば（`SELECT app_id FROM canvas_apps WHERE deployed = true LIMIT 1`）、`http://localhost:5173/orochi/apps/{app_id}/` を開いて動作が壊れていないこと（特に `ai()` 呼び出しがある場合）を確認。model 未指定でも Haiku で応答が返ること。
  </how-to-verify>
  <resume-signal>"approved" または具体的な問題を報告</resume-signal>
</task>

</tasks>

<verification>
- `uv run pytest tests/jobs/handlers/test_iframe_rpc_handler_ai.py -q` グリーン
- `uv run ruff check app/jobs/handlers/iframe_rpc_handler.py` クリーン
- 人手確認: Haiku 既定 / sonnet エイリアス / 無効値拒否の 3 ケース、および既存デプロイ済み Canvas アプリの後方互換
</verification>

<success_criteria>
- Canvas アプリの iframe JS から `ai(prompt)`（model 未指定）で Haiku 応答が返る
- `ai(prompt, { model: 'sonnet' })` で Sonnet 応答が返る
- `ai(prompt, { model: 'claude-sonnet-4-6' })` で実 ID 直指定も動作する
- `ai(prompt, { model: 'turbo' })` は `{result: false, error: ...}` を返し Copilot を呼ばない
- 旧 `ai(prompt, 30000)` 形式の Canvas アプリが引き続き動作する
- `test_iframe_rpc_handler_ai.py` の 8 テストすべてグリーン
</success_criteria>

<output>
完了後、`.planning/quick/260415-mbc-canvas-ai/260415-mbc-SUMMARY.md` を作成する。
</output>

---

## スコープ外 (Deferred — 別 Todo 候補)

本 quick タスクでは **リクエスト毎の model パラメータのみ** を実装する。以下は意図的にスコープ外とし、別 Todo として切り出すことを推奨する:

1. **Canvas アプリ単位のデフォルトモデル永続化:**
   `canvas_apps` テーブルに `default_model TEXT` カラムを追加し、リクエストの優先順位を「リクエスト param > アプリ設定 > システムデフォルト(Haiku)」にする。DB マイグレーション + `canvas.py` CRUD + 編集 UI（アプリごとの設定ダイアログ）が必要で、quick の粒度を超える。

2. **`langgraph_handler.py:52` および `iframe_rpc_handler.py:123` の既存ハードコード `claude-sonnet-4.5`（実在しない可能性）の是正:**
   通常チャット / SuperChat 経路のモデル指定も整理する必要があるが、影響範囲が広く別途調査が必要。本 quick では触らない。

3. **モデルカタログの config.yaml 化:**
   `MODEL_ALIASES` を Python 定数から `config/models.yaml` に移動し、起動時読み込みにする。モデル追加を再デプロイなしで可能にする。現状 3 モデルのみなのでハードコードで十分。

4. **モデル別コスト/レイテンシのメトリクス記録:**
   200 名運用の監査ログ観点で、どのアプリがどのモデルをどれだけ使っているかの計測が将来必要。
