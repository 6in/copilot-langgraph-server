---
status: complete
phase: 22-web-search-tavily
source: [22-01-SUMMARY.md, 22-02-SUMMARY.md]
started: 2026-04-10T00:00:00Z
updated: 2026-04-13T00:00:00Z
---

## Current Test

[testing complete — all gaps closed]

## Tests

### 1. Cold Start Smoke Test
expected: docker compose down && docker compose up でコンテナが全て起動する。mcp-server コンテナが healthy になり、/health が 200 OK を返す。
result: pass

### 2. web_search ツール登録確認
expected: mcp-server で "web_search" ツールが登録されていることが確認できる（"web_search_stub" は存在しない）。
result: pass

### 3. エージェントへの Web 検索質問
expected: SuperChat で general-assistant を選び、リアルタイム情報が必要な質問をすると web_search ツールが呼ばれ Tavily の情報を含む回答が返る。
result: pass
reported: "「本日は2026年4月13日です。明日の東京の目黒区の天気は？」→ Claude Sonnet 4.6 (general-assistant) が web_search を呼び出し、曇り/23℃/15℃ の予報と Toshin.com の URL を含む回答が返った。"
note: "GPT-4.1 (Copilot) はアーキテクチャ知識からツール呼び出し JSON の出力を拒否。Claude Sonnet 4.6 は TOOL_SYSTEM_PROMPT_TEMPLATE の JSON 指示に正しく従う。AGENT.md の model: claude-sonnet-4-6 で解決。"

### 4. 検索結果サイズ制限
expected: 調査系の質問をしてもコンテキスト超過エラーが発生せず、web_search が呼ばれて Tavily 情報を含む回答が返ってくる。
result: pass
reported: "天気検索で web_search が正常に呼ばれ、max_results=3 制限により回答長も適切。コンテキスト超過エラーなし。"

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "エージェントへの質問で web_search ツールが自動的に呼び出され、Tavily から取得した情報が回答に含まれる"
  status: closed
  resolution: "TOOL_SYSTEM_PROMPT_TEMPLATE をシンプルな JSON 指示形式に整理。general-assistant の model を claude-sonnet-4-6 に設定（AGENT.md 既定値）。Claude Sonnet 4.6 は JSON ツール呼び出し指示に正しく従い web_search を実行する。"
  closed_at: "2026-04-13"

- truth: "検索系の質問で web_search が呼ばれ、コンテキスト超過なく Tavily 情報を含む回答が返る"
  status: closed
  resolution: "テスト3の解決により同時に解消。天気検索で正常動作確認済み。source_urls が回答に引用される。"
  closed_at: "2026-04-13"
