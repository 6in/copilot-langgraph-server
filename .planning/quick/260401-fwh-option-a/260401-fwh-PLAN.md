---
phase: quick
plan: 260401-fwh
type: execute
wave: 1
depends_on: []
files_modified:
  - app/providers/copilot.py
  - app/graph/builder.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "Copilot SDK のツール実行ループが動作する (on_permission_request が approve_all を使う)"
    - "builder.py が SystemMessage でツールなしと指示しない (シンプルな chatbot_node)"
  artifacts:
    - path: "app/providers/copilot.py"
      provides: "on_permission_request=PermissionHandler.approve_all に戻した create_session 呼び出し"
    - path: "app/graph/builder.py"
      provides: "_system_msg なし、state['messages'] をそのまま llm.ainvoke に渡す chatbot_node"
  key_links:
    - from: "app/providers/copilot.py"
      to: "copilot.PermissionHandler.approve_all"
      via: "create_session(on_permission_request=PermissionHandler.approve_all)"
      pattern: "PermissionHandler\\.approve_all"
---

<objective>
SDK のツールを Option A（approve_all）で有効化する。

Purpose: 直前の 260401-f4x で入れたハルシネーション回避策（lambda _: False + SystemMessage "no tools"）を取り除き、SDK ネイティブのツール実行ループを使う。モデルがファイル参照や検索などの SDK ビルトインツールを実際に実行できるようになる。

Output:
- app/providers/copilot.py — on_permission_request を PermissionHandler.approve_all に戻す
- app/graph/builder.py — _system_msg と prepend ロジックを削除し chatbot_node をシンプルに戻す
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: copilot.py — on_permission_request を approve_all に戻す</name>
  <files>app/providers/copilot.py</files>
  <action>
    `_agenerate` 内の `create_session` 呼び出しを修正する。

    現在:
    ```python
    session = await self._client.create_session(
        on_permission_request=lambda _: False,  # deny all SDK tools to prevent hallucination
        model=self.model,
    )
    ```

    変更後:
    ```python
    session = await self._client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        model=self.model,
    )
    ```

    `PermissionHandler` はファイル冒頭の SDK import 行ですでにインポート済みなので追加 import 不要。
    コメント (`# deny all ...`) も削除する。
  </action>
  <verify>
    <automated>grep -n "approve_all\|lambda _: False" app/providers/copilot.py</automated>
  </verify>
  <done>
    - `approve_all` が create_session に渡されている
    - `lambda _: False` の行が存在しない
  </done>
</task>

<task type="auto">
  <name>Task 2: builder.py — SystemMessage を削除してシンプルな chatbot_node に戻す</name>
  <files>app/graph/builder.py</files>
  <action>
    `build_graph` 関数から `_system_msg` の定義と chatbot_node 内の prepend ロジックを削除する。

    現在:
    ```python
    _system_msg = SystemMessage(
        content="You have no tools available. Respond to all requests using text only."
    )

    async def chatbot_node(state: MessagesState) -> dict:
        messages = [_system_msg] + list(state["messages"])
        response = await llm.ainvoke(messages)
        return {"messages": [response]}
    ```

    変更後:
    ```python
    async def chatbot_node(state: MessagesState) -> dict:
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response]}
    ```

    `SystemMessage` はこのファイルの import 行からも削除する（他で使われていないため）。
    具体的には以下の行を削除:
    ```python
    from langchain_core.messages import SystemMessage
    ```
  </action>
  <verify>
    <automated>grep -n "SystemMessage\|_system_msg\|no tools" app/graph/builder.py</automated>
  </verify>
  <done>
    - `_system_msg` の定義が存在しない
    - `[_system_msg] +` の prepend が存在しない
    - `SystemMessage` import が存在しない
    - `chatbot_node` が `state["messages"]` を直接 `llm.ainvoke` に渡している
  </done>
</task>

</tasks>

<verification>
両ファイルの変更後、既存テストが通ることを確認する:

```bash
python -m pytest tests/ -x -q 2>&1 | tail -20
```

エラーがなければ OK。テストが graph や provider をカバーしていれば結合の整合性も保証される。
</verification>

<success_criteria>
- app/providers/copilot.py: `create_session(on_permission_request=PermissionHandler.approve_all, ...)` になっている
- app/graph/builder.py: `_system_msg` なし、`state["messages"]` をそのまま `ainvoke` に渡している
- 既存テスト (pytest) がパスしている
</success_criteria>

<output>
After completion, create `.planning/quick/260401-fwh-option-a/260401-fwh-SUMMARY.md`
</output>
