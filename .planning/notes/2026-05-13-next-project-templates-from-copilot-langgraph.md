---
date: "2026-05-13 11:51"
promoted: false
---

次のプロジェクト作成時に、現在のプロジェクト (copilot-langgraph) から各種雛形を作成する。特に整理したい論点: (1) ADR vs Phase Retrospective の役割分離 — 現プロジェクトでは /create-adr を振り返り目的で使ってきたが本来は「意思決定の記録」が ADR で、振り返りは別フォーマット (例: docs/retrospectives/ や .planning/notes/) が筋。新プロジェクトでは最初から分けて立ち上げる。(2) GSD ワークフロー雛形 (CLAUDE.md / patterns.md / adr-categories.yaml / scripts/install-hooks.sh / scripts/generate_adr_index.py)。(3) Docker Compose の dev server watch noise 隔離設定 (ADR-0054 由来: uvicorn --reload-dir whitelist + Vite server.watch.ignored)。(4) MCP ツールカタログの single source of truth 構造 (config/mcp_tools.yaml + 自動生成 3 ファイル + drift 検知 hook)。本プロジェクトはこのまま運用継続、リネームや遡及修正はしない方針。
