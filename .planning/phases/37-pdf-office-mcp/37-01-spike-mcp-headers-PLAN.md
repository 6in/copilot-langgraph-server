---
phase: 37
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - work/phase-37/spike-mcp-headers.md
  - tests/test_mcp_client_headers.py
autonomous: true
requirements: [FIN-04]
estimated_minutes: 50
tags: [mcp, fastmcp, rpc-context, spike]

must_haves:
  truths:
    - "作業ブランチ `gsd/phase-37-pdf-office-mcp` 上で作業が開始されている (CLAUDE.md ブランチ必須ルール遵守)"
    - "MultiServerMCPClient が streamable_http 接続に headers を添えてツールコールを転送するか判定できている"
    - "判定結果が明確な採用可否(採用 / フォールバックへ切替)として文書化されている"
    - "Plan 03 Task 3 が 1 本道 (Route A または Route B のどちらか一方) で実装できる状態になっている"
  artifacts:
    - path: "work/phase-37/spike-mcp-headers.md"
      provides: "MultiServerMCPClient headers サポート検証レポート"
      contains: "## 結論"
    - path: "tests/test_mcp_client_headers.py"
      provides: "Wave 0 向け試験テスト (xfail または skip 付きでもよい)"
      contains: "def test_"
  key_links:
    - from: "tests/test_mcp_client_headers.py"
      to: "MultiServerMCPClient"
      via: "streamable_http 経由のモック / live test"
      pattern: "MultiServerMCPClient"
---

<objective>
Phase 37 の最大の設計課題である「MCP プロトコル経由で RPCContext を mcp-server に届ける手段」を
Wave 1 実装に先立って確定させる。RESEARCH.md Open Question Q1 / Assumption A1 を潰し、
以下 2 分岐のどちらを採用するかを決定する。

- **Route A**: `MultiServerMCPClient({"copilot-tools": {"transport": "streamable_http", "url": ..., "headers": {"x-thread-id": ..., "x-github-login": ...}}})` で
  ヘッダーを各 tool call に自動で付与できる場合 → FastMCP `CurrentHeaders()` 経由で受け取る実装で進める
- **Route B**: 上記が動作しない場合 → mcp-server に専用 REST エンドポイント
  `/internal/attachments_list` / `/internal/attachments_extract` を追加し、worker から `httpx` 直接呼び出しでヘッダーを付ける fallback 実装で進める

Purpose: Wave 1 の `attachments_*` 実装で採用する RPCContext 伝播経路を確定させる
Output: `work/phase-37/spike-mcp-headers.md` に結論と証拠ログ、`tests/test_mcp_client_headers.py` に検証スケルトン
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/37-pdf-office-mcp/37-CONTEXT.md
@.planning/phases/37-pdf-office-mcp/37-RESEARCH.md
@.planning/phases/37-pdf-office-mcp/37-PATTERNS.md

<interfaces>
<!-- Wave 0 スパイクで触れる既存インターフェース -->

From app/jobs/worker.py (L70-92):
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

mcp_url = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001") + "/mcp"
mcp_client = MultiServerMCPClient({
    "copilot-tools": {
        "transport": "streamable_http",
        "url": mcp_url,
    }
})
mcp_tools_loaded = await mcp_client.get_tools()
```

From fastmcp.dependencies (verified 3.2.3):
```python
from fastmcp.dependencies import CurrentHeaders

@mcp.tool
async def some_tool(headers: dict = CurrentHeaders()) -> dict:
    # headers.get("x-thread-id") — lowercase key
    ...
```

From mcp_server/server.py (L64-100) — 既存の `/internal/call_tool` エンドポイントパターン:
```python
@mcp.custom_route("/internal/call_tool", methods=["POST"])
async def internal_call_tool(request: Request) -> JSONResponse:
    body = await request.json()
    call_result = await mcp.call_tool(tool_name, args)
    ...
```
</interfaces>

<skills>
- Context7 MCP: `MultiServerMCPClient` / `langchain-mcp-adapters` のドキュメント検索で `headers` オプションの有無を一次確認できる
  - 例: `mcp__context7__resolve-library-id "langchain-mcp-adapters"` → `get-library-docs` で `headers` キーワード検索
</skills>
</context>

<tasks>

<task type="auto">
  <name>Task 0: ブランチ確認 / 作成 (CLAUDE.md 必須ルール)</name>
  <files>(git branch state only)</files>
  <read_first>
    - CLAUDE.md §"GSD Workflow Enforcement" (ブランチ必須ルール)
    - feedback_branch_required_for_quick.md (gsd-quick でも必ずブランチ作成)
  </read_first>
  <action>
  CLAUDE.md のブランチ必須ルールに従い、Phase 37 作業ブランチが切られていることを確認する。
  既に `gsd/phase-37-pdf-office-mcp` 上で作業している場合はそのまま続行。それ以外なら以下を実行する。

  ```bash
  # 現在のブランチを確認
  CURRENT=$(git branch --show-current)
  echo "Current branch: $CURRENT"

  if [ "$CURRENT" = "gsd/phase-37-pdf-office-mcp" ]; then
    echo "既に Phase 37 ブランチ上。続行。"
  elif [ "$CURRENT" = "main" ]; then
    # main から新規作成
    git checkout -b gsd/phase-37-pdf-office-mcp
  else
    # 他ブランチから main 経由で作成するか、直接 checkout -b
    # ユーザーに確認が必要なら Discuss モードへフォールバック
    git checkout -b gsd/phase-37-pdf-office-mcp
  fi

  # 最終確認
  git branch --show-current
  ```

  本 Task は 2 秒で終わる軽作業だが、CLAUDE.md の "main ブランチ上で直接コミットしない" 要件を満たすため
  Plan 01 の Task 1/2 より前に明示的に存在させる。
  </action>
  <verify>
    <automated>test "$(git branch --show-current)" = "gsd/phase-37-pdf-office-mcp"</automated>
  </verify>
  <acceptance_criteria>
    - `git branch --show-current` の出力が `gsd/phase-37-pdf-office-mcp` と完全一致
    - `git status` でワーキングツリーが壊れていない (リポジトリ状態が healthy)
  </acceptance_criteria>
  <done>Phase 37 作業ブランチが確実にアクティブ</done>
</task>

<task type="auto">
  <name>Task 1: MultiServerMCPClient headers オプション検証</name>
  <files>work/phase-37/spike-mcp-headers.md</files>
  <read_first>
    - .planning/phases/37-pdf-office-mcp/37-RESEARCH.md (特に Open Questions Q1 / Assumption A1 / Libraries and APIs セクション)
    - app/jobs/worker.py L70-92 (既存 MCP client 設定)
    - mcp_server/server.py L1-108 (FastMCP エントリ + /internal/call_tool パターン)
  </read_first>
  <action>
  3 段階で検証を行い `work/phase-37/spike-mcp-headers.md` に結論を記録する。

  **手順 1: ソース直接確認**
  ```bash
  python3 -c "from langchain_mcp_adapters.client import MultiServerMCPClient; import inspect; print(inspect.getsourcefile(MultiServerMCPClient))"
  # 返ったファイルを cat/Read し、streamable_http 接続設定の schema に "headers" キーがあるか確認
  ```

  `langchain_mcp_adapters/sessions.py` (もしくは同等ファイル) の `StreamableHttpConnection` TypedDict の
  `headers: NotRequired[dict[str, str] | None]` 等のフィールド有無を確認する。

  **手順 2: 実接続テスト (Context7 / GitHub どちらか実装が読めるもので判断がつけば実接続はスキップ可)**
  ローカルで `docker compose up mcp-server -d` 後に以下の最小スクリプトで確認:

  ```python
  import asyncio
  from langchain_mcp_adapters.client import MultiServerMCPClient

  async def main():
      client = MultiServerMCPClient({
          "copilot-tools": {
              "transport": "streamable_http",
              "url": "http://localhost:8001/mcp",
              "headers": {"x-thread-id": "spike-t", "x-github-login": "spike-u"},
          }
      })
      tools = await client.get_tools()
      # ping ツールを呼んで mcp-server のログに x-thread-id が届くか観察
      for t in tools:
          if t.name == "ping":
              result = await t.ainvoke({})
              print(result)

  asyncio.run(main())
  ```

  事前に mcp-server server.py の `ping` ツールに一時的に `logger.info` を入れて
  `CurrentHeaders()` の値を吐かせる (スパイク後に revert)。

  **手順 3: 結論を work/phase-37/spike-mcp-headers.md に記載**
  テンプレート:
  ```markdown
  # Phase 37 Spike: MultiServerMCPClient headers サポート

  **Date:** YYYY-MM-DD
  **Version:** langchain-mcp-adapters X.Y.Z
  **Verdict:** Route A 採用 / Route B 採用

  ## 証拠

  1. ソース確認結果 (ファイル + 行番号 + TypedDict の該当フィールド引用)
  2. 実接続ログ (mcp-server 側で見えた x-thread-id / x-github-login)

  ## 結論

  - Route A (MCP headers 採用) の場合: attachments_list/extract は `@mcp.tool` + `CurrentHeaders()` で実装する
  - Route B (フォールバック) の場合: mcp-server に `/internal/attachments_*` REST エンドポイントを追加し、worker の LangGraphHandler から `httpx` で直接呼び出すラッパーツールを ToolEnabledSubAgent に登録する

  ## Wave 1 への影響

  Plan 03 (37-03-mcp-attachments-tools) の設計を上記 Verdict に沿って確定させる。
  Plan 03 Task 3 の実装コードは本文書の Verdict のみを 1 経路実装し、不採用ルートのコードは削除する。
  ```

  ※ このスパイクはアプリコードを恒久変更しない。結論と一時的に追加したログは revert する (結論文書だけ残す)。
  </action>
  <verify>
    <automated>test -s work/phase-37/spike-mcp-headers.md && grep -E "Verdict:\s*(Route A|Route B)" work/phase-37/spike-mcp-headers.md</automated>
  </verify>
  <acceptance_criteria>
    - `work/phase-37/spike-mcp-headers.md` が存在し 20 行以上ある
    - ファイル内に `Verdict: Route A` または `Verdict: Route B` のいずれか 1 行が存在する
    - ファイル内に `langchain-mcp-adapters` の version 情報が含まれる (`pip show langchain-mcp-adapters | grep Version` の実ログ貼付)
    - Route A 採用の場合は `mcp-server 側ログに x-thread-id が届いた証拠` が貼付されている
    - Route B 採用の場合は `headers フィールドが TypedDict に存在しない` もしくは `実接続で届かなかった` ことの根拠行が貼付されている
    - Wave 1 への影響セクションに "Plan 03 Task 3 は Verdict の 1 経路のみ実装する" 旨が明記されている
  </acceptance_criteria>
  <done>Spike verdict がコミットされ、Wave 1 プランの実装経路が一意に定まる</done>
</task>

<task type="auto">
  <name>Task 2: Wave 0 試験テストスケルトン追加</name>
  <files>tests/test_mcp_client_headers.py</files>
  <read_first>
    - tests/test_mcp_server.py L1-80 (FastMCP in-process Client パターン)
    - work/phase-37/spike-mcp-headers.md (Task 1 の結果)
  </read_first>
  <action>
  Task 1 の Verdict に応じて最小の試験テストを追加する。Route A/B いずれでも後続 plan で grow させる骨組み。

  ```python
  """Phase 37 Wave 0 spike follow-up: RPCContext propagation smoke test.

  Verdict from work/phase-37/spike-mcp-headers.md determines which route to exercise.
  This file intentionally contains only a smoke/xfail-able assertion so Wave 1 can
  replace it with the real RPCContext-propagation tests.
  """
  from __future__ import annotations

  import pytest


  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 1 で本実装が入るまで保留", strict=False)
  async def test_mcp_context_headers_smoke():
      """Route A 採用時: MultiServerMCPClient が x-thread-id を転送し、
      mcp-server 側の @mcp.tool が CurrentHeaders() で受け取れる前提の smoke test。

      Route B 採用時: このテストは scope outside となり Plan 03 で削除または
      /internal/attachments_* の httpx 呼び出しテストに差し替える。
      """
      assert True  # Wave 1 で実装置換
  ```

  Route B 採用の場合は xfail 理由と TODO コメントでその旨を明記する:
  ```python
  @pytest.mark.skip(reason="Route B (httpx 直接呼び出し) 採用のため Plan 03 で書き換え予定")
  ```
  </action>
  <verify>
    <automated>uv run pytest tests/test_mcp_client_headers.py -v --no-header 2>&1 | grep -E "(xfail|skipped|passed)"</automated>
  </verify>
  <acceptance_criteria>
    - `tests/test_mcp_client_headers.py` が存在
    - `pytest tests/test_mcp_client_headers.py` が xfail または skip で実行される (no hard failure)
    - ファイル docstring に `Phase 37 Wave 0 spike follow-up` の記述がある
    - `work/phase-37/spike-mcp-headers.md` の Verdict と整合する注記がテスト docstring にある
  </acceptance_criteria>
  <done>Wave 0 で整備した spike 骨組みが commit される</done>
</task>

</tasks>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| worker → mcp-server (streamable_http) | スパイク中に一時的に観察する HTTP ヘッダー経路 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-37-SP-01 | Information Disclosure | spike 時の temporary logging of RPCContext | mitigate | ログ追加はスパイク内で revert すること (受け入れ基準に明記)。git diff で本番 `mcp_server/server.py` に残存していないか確認 |
| T-37-SP-02 | Tampering | フォールバック (Route B) 採用時に `/internal/attachments_*` エンドポイントが localhost 以外から届かないか | accept (scope for Plan 03) | mcp-server はホストポート非公開 (既存 ADR-0020)。Plan 03 で endpoint 追加時に内部ネットワーク専用を再確認する |

</threat_model>

<verification>
- `git branch --show-current` が `gsd/phase-37-pdf-office-mcp`
- `test -s work/phase-37/spike-mcp-headers.md` で空でない結論文書の存在確認
- `grep "Verdict:" work/phase-37/spike-mcp-headers.md` で結論行の存在確認
- `uv run pytest tests/test_mcp_client_headers.py -v` が non-failure で終了する (xfail / skip / pass)
- `git diff mcp_server/server.py` がクリーン (スパイク用ログを revert してあるか)
</verification>

<success_criteria>
- 作業が Phase 37 専用ブランチ上で開始されている (CLAUDE.md 準拠)
- Route A / Route B のどちらかに Verdict が確定し、Wave 1 の実装方針が一意に決まる
- Plan 03 が「Route A なら CurrentHeaders()、Route B なら httpx 直接呼び出し」の条件分岐を含まずに 1 本道で書ける状態になる
- 本番コードに spike 用の一時ログ追加が残っていない
</success_criteria>

<output>
After completion, create `.planning/phases/37-pdf-office-mcp/37-01-SUMMARY.md` with:
- Spike verdict 要約 (Route A / Route B)
- 根拠 (ソース確認 + 実接続ログ抜粋)
- Wave 1 プランへの引き渡し事項
</output>
