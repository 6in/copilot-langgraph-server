---
created: 2026-05-13T13:45:45.996Z
title: チャットシステムで何が実行可能なのかを整理 — ツール・エージェント・各アプリの概要
area: docs
files:
  - README.md
  - docs/mcp-tools.md
  - config/mcp_tools.yaml
  - agents/*/AGENT.md
  - app/orchestrator/agent.py
  - app/orchestrator/tool_agent.py
  - frontend/src/components/MenuScreen.tsx
---

## Problem

利用者 (本番ユーザ 200 名規模) や新規開発者向けに「このシステムで何ができるか」を一望できるドキュメントが現状ない。情報は以下のように散らばっていて、全体像を掴むには複数ファイル横断が必要:

- **アプリ別の機能と用途**: README.md に概要表はあるが「いつどれを使うか」「アプリ間で何が違うか」の利用者目線整理がない。Chat / SuperChat / Gems / Canvas / Debate / (HostedApps?) の判断基準が暗黙
- **MCP ツール一覧**: `docs/mcp-tools.md` (自動生成) と `config/mcp_tools.yaml` (SSoT) はあるが、技術ドキュメント寄りで「これでこんなことができる」というユースケース視点ではない
- **エージェント (SubAgent) の種類**: `agents/<slug>/AGENT.md` 群が個別に存在、SubAgentRegistry が自動ロードしているが、利用者から見て「SuperChat で選べるエージェントとそれぞれの得意分野」を一覧する場所がない
- **Gem テンプレ**: DB に保存される動的 entity だが、初期テンプレや典型用途の例が見当たらない
- **新規ユーザ onboarding**: ログイン後に最初に何を試せばいいかの hints がない

特に本番デプロイで 200 名にロールアウトする段階では、「とりあえずこのドキュメントを読めば 80% わかる」という導入ガイドが必要。

## Solution

**ドキュメントの構成案** (1 ファイルにまとめるか、章立てで分割):

### Part 1: ユーザ向け概要 (`README.user.md` or similar)

- 5 アプリの判断フローチャート (こういう時はどれを使う):
  - 単発の質問 → Chat
  - 専門家エージェントに振り分けて欲しい → SuperChat
  - 自分専用の指示書を Gem として保存 → Gems
  - HTML/JS で動くミニアプリを作る → Canvas
  - 複数 AI に同じ議題を順番に話させる → Debate
- 各アプリのスクリーンショット + できること例
- 添付ファイル (📎) で何ができるか (Phase 36/37/38 機能の利用者視点まとめ)

### Part 2: ツールカタログ (利用者視点、`docs/tools-for-users.md` 等)

- `docs/mcp-tools.md` (自動生成) を補完する形で、各 MCP ツールの **ユーザ視点ユースケース** を整理
- 例: web_search なら「最新情報を聞きたい時に AI が裏で検索する」、db_query なら「データ集計を頼める」、claude_code なら「ファイル生成/コード実行を頼める」
- ツールがどのアプリで利用可能か (Chat/SuperChat/Gem/Canvas/Debate のマトリクス)

### Part 3: エージェントカタログ

- SuperChat で選択可能な agent (`agents/*/AGENT.md`) 一覧 + 各 agent の専門分野・典型クエリ例
- Gem として保存された「ユーザ作成 agent」との違い

### Part 4: 開発者向け (`README.dev.md`)

- システム構成 (README.md の「アーキテクチャ」セクション拡充)
- 新規ツール追加 (`/add-mcp-tool` 既存手順への参照)
- 新規エージェント追加 (`agents/<slug>/AGENT.md` 規約)
- ADR / patterns.md の読み方

**実装アプローチの選択肢**:

| 案 | 工数 | 効果 |
|---|------|------|
| A. README.md を章立てで大幅拡充 + 既存 docs/ から transclude | 中 | 既存資産活用、メンテ二重化なし |
| B. ユーザ向け / 開発者向けで README を分離 | 中 | onboarding 体験が明確、メンテファイル増 |
| C. docs/ 配下に index.md を作って既存ドキュメントへの reading order を提示 | 小 | 既存資産そのまま、整理コスト最小 |

推奨: **C → A** の順で漸進的に。まず C で「読む順番」を整え、不足部分が見えてきたら A で本格的に章を起こす。

## Out of Scope

- このタスクで触らないもの:
  - 既存 `.planning/PROJECT.md` (内部企画ドキュメント、ユーザ向けではない)
  - 個別 ADR (`docs/adr/`) (設計判断記録なので onboarding ドキュメントとは別軸)
  - i18n (本番ユーザは日本語想定、英語ローカライズは別 phase で検討)

## Related

- Phase 32 (AI-UI 操作基盤、未着手) で `data-ai-role` 属性が入ると、ドキュメント自体を AI に読ませるユースケースも検討可能
- 本番ロールアウト前 (v6.0 milestone close 前) に Part 1 だけでも揃えたい
- Phase 36/37/38 で確立した「添付 → AI が読む / AI が生成」フローはユーザ視点で説明が薄いので、このドキュメント整備のタイミングで利用例を充実させたい
