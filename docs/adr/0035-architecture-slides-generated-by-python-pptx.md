# 0035. アーキテクチャ説明資料を python-pptx で生成する

**Date:** 2026-04-15
**Status:** Accepted

## Context

Copilot LangGraph Chat の仕組み（FastAPI + arq worker + LangGraph + ChatCopilot + MCP + PostgreSQL/Redis）を他者へ説明するためのスライド資料が存在しなかった。口頭説明では Device Flow → JWT、POST → job_id → SSE、ChatCopilot/BoundChatCopilot → ToolNode のループなど、複数レイヤーに跨がる設計意図が伝わりにくい。

要件:

- 一枚絵のアーキ図ではなく、プロジェクト概要・5 アプリ紹介・全体構成・認証・非同期ジョブ・LangGraph・SubAgent+MCP・永続化・拡張計画を順序立てて説明したい。
- スライドの内容は進化するので、差分管理とレビューができる形で持ちたい。
- 最終成果物は社内共有のために `.pptx` で出力する必要がある。

## Decision

`docs/slides/generate_architecture.py` として python-pptx ベースの生成スクリプトを配置し、`docs/slides/architecture.pptx` を成果物としてコミットする。

- スクリプトは 16:9 (13.33 × 7.5 inch) でスライドを組み立てる。見出し帯・丸角ボックス・矢印コネクタを共通ヘルパ (`_add_box` / `_add_arrow` / `_add_section_header`) で描画する。
- フォントは日本語対応のため Meiryo を指定。
- 生成は社内向けの一度きりのドキュメント作業なので、プロジェクト本体の `pyproject.toml` には python-pptx を追加せず、ユーザー側の scratch venv（例: `/tmp/pptx-venv`）に `python-pptx` + `lxml` をインストールして走らせる。
- 内容は 11 枚構成: タイトル / 概要 / 5 アプリ / 全体構成 / Device Flow / 非同期ジョブ / LangGraph / SubAgent + MCP / 永続化 / 拡張計画 / Q&A。

## Alternatives Considered

- **Marp / Slidev (Markdown → スライド)**: Markdown で管理できる点は魅力だが、`.pptx` への変換が画像経由になり再編集性が落ちる。また、ボックス・矢印レイアウトの細かな制御が難しい。今回は `.pptx` 直接出力を優先して不採用。
- **手書きの .pptx をそのまま commit**: バージョン管理は効かず、差分レビューができないため却下。
- **python-pptx を本体 `pyproject.toml` に追加**: 本体アプリでは利用しないため、依存関係を汚さないよう不採用。scratch venv で生成する運用にした。

## Consequences

### Positive

- 構成が変わっても `generate_architecture.py` を編集 → 再実行するだけで `.pptx` が再生成できる。
- コード差分でスライド変更をレビューできる。
- フォント・色・レイアウトが共通ヘルパ化されているので、スライドを増やす際のコストが低い。

### Negative / Gotchas

- python-pptx は本体 venv に入っていない。再生成時は別 venv を作る必要がある:
  ```bash
  uv venv --python 3.12 /tmp/pptx-venv
  uv pip install --python /tmp/pptx-venv/bin/python python-pptx lxml
  /tmp/pptx-venv/bin/python docs/slides/generate_architecture.py
  ```
- `_set_text` の初期実装で `p.runs == []` として空判定していたが、`runs` は tuple のため常に True にならず `IndexError` となった。`len(p.runs) > 0` で判定する必要がある（同種のヘルパを追加する際の落とし穴）。
- LibreOffice で開くと `.~lock.architecture.pptx#` が生成される。コミット前に閉じておく。
- 生成物 `.pptx` (約 47 KiB) をバイナリとしてコミットしているため、頻繁に差し替えると履歴が肥大化する。大幅な内容変更時はスクリプト PR とセットで運用する。
