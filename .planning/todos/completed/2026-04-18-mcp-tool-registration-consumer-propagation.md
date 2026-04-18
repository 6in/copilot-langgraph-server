---
created: 2026-04-18T00:00:00Z
title: MCP ツール追加時の consumer 伝播・管理方法を整理する
area: api
files:
  - mcp_server/tools/
  - config/mcp_tools.yaml
  - mcp_server/tools/mcp_helper.py
  - static/js/iframe-rpc.js
  - agents/*/AGENT.md
  - scripts/sync-tool-list-to-js.py
---

## Problem

MCP サーバーに新しいツールを 1 つ追加すると、**3 箇所の consumer に手作業でフック追加が必要**。
どこに何を追加する必要があるかが開発者の暗黙知に依存していて、追加漏れに気付きにくい。

| Consumer | 追加作業 | 現状の自動化 |
|----------|---------|------------|
| ToolEnabledSubAgent | `agents/<name>/AGENT.md` の `tools:` に追記 | ToolRegistry が `config/mcp_tools.yaml` と MCP 実ツールの一致検証のみ（consumer 側は見ない） |
| CodeActSubAgent (`mcp_helper.py`) | `search`/`query_db`/`get_datetime` のように Python ラッパー関数を手書きで追加 | なし — 追加忘れると sandbox 内コードから呼べない |
| iframe-rpc (`static/js/iframe-rpc.js`) | `AVAILABLE_TOOLS` 定数に tool 情報を追記 | `scripts/sync-tool-list-to-js.py` で `config/mcp_tools.yaml` から同期可能 |

また、そもそも「どの consumer にそのツールを公開すべきか」の判断基準も明文化されていない。
例: `claude_code` は privileged なので iframe-rpc に露出すべきではない、execute_python は CodeAct 専用で SubAgent には与えない、など。

## 関連する ADR・パターン

- ADR 0024: MCP ツールカタログ検証 (ToolRegistry) — `config/mcp_tools.yaml` ↔ 実ツール一致検証
- ADR 0040: `iframe-rpc.js` ツールカタログ埋め込み + 同期スクリプト
- ADR 0041: CodeAct 直接実行方式（mcp_helper 経由）
- `.planning/patterns.md` の「FastMCP Docker 独立サービス基盤」「MCP ツールカタログ YAML 検証」

## 議論したい論点

1. **ツール宣言の single source of truth** は `config/mcp_tools.yaml` のままでよいか / メタデータ追加（expose_to: [subagent, codeact, iframe] 等）で consumer への公開先を YAML で宣言できるようにするか
2. **自動生成できる範囲の特定** — AVAILABLE_TOOLS（JS）は既に同期スクリプトあり。mcp_helper.py の Python ラッパーは生成可能か？ AGENT.md の `tools:` は生成対象外（人間判断）
3. **チェックリスト or CI チェック** — 新規ツール追加時に漏れを検知する pre-commit / CI の仕組み
4. **ドキュメント/ハンドブック** — `docs/mcp-tool-add.md` のような追加手順書を整備するか、コードによる強制に寄せるか
5. **privileged ツールの露出制御** — consumer 側で privileged の扱いをどう強制するか（ToolRegistry WARNING だけでは iframe/CodeAct をカバーしない）

## Solution（方向性のたたき台）

- `config/mcp_tools.yaml` のツールエントリに `consumers: [subagent, codeact, iframe]` のような公開先リストを追加
- mcp_helper.py の関数・iframe-rpc の AVAILABLE_TOOLS を `config/mcp_tools.yaml` から自動生成（型情報・docstring はメタデータとして YAML に持たせる）
- 追加手順書 `docs/add-mcp-tool.md` をチェックリスト化
- pre-commit hook で YAML → mcp_helper.py / iframe-rpc.js の乖離を検知

## Notes

- 当初 Phase 30 として ROADMAP に「MCP ツール利用の監査ログ + 影響範囲可視化」というタイトルで登録されていたが、本来のユーザー意図は「consumer 伝播・管理方法」だった。Phase 30 は 2026-04-18 に /gsd-remove-phase で削除済み。audit log / visualization は別トピックとして v5.1+ の Deferred。
