# Requirements: v3.0 Agent Platform

> Milestone goal: 50エージェント・複数アプリケーションに耐えるマルチエージェントプラットフォーム基盤を構築し、エージェント追加・組み合わせをユーザー体験の核心にする。

## v3.0 Requirements

### REGISTRY — SubAgentRegistry 強化

- [ ] **REGISTRY-01**: ユーザーがフォルダ定義型エージェント（AGENT.md + tools/）を agents/ に配置するだけでシステムが自動ロードできる
- [ ] **REGISTRY-02**: ユーザーがコード実装型エージェント（AGENT.md + agent.py）を配置した場合、agent.py の SubAgent 実装がフォルダ型より優先使用される
- [ ] **REGISTRY-03**: エージェントの初期化失敗が FAILED / 外部依存エラーが DEGRADED に分類され、1つの障害がシステム全体を止めない
- [ ] **REGISTRY-04**: ユーザーが GET /health/agents で全エージェントのステータス（HEALTHY/DEGRADED/FAILED）と障害理由を確認できる

### APP — アプリケーションパッケージ

- [ ] **APP-01**: 開発者がアプリ定義ファイルに使用エージェントのリストを宣言することで、50個のエージェントからサブセットをパッケージ化できる
- [ ] **APP-02**: ユーザーがメニュー画面からアプリケーションを選択すると、そのアプリ専用のチャット画面が起動する
- [ ] **APP-03**: 各アプリの RouterNode はそのアプリに割り当てられたエージェントのみを候補としてルーティングする（他のエージェントは見えない）
- [ ] **APP-04**: 1つのエージェント定義を複数のアプリケーションで共有利用できる（定義は agents/ の1か所のみ）

### ROUTING — ルーティング品質

- [ ] **ROUTING-01**: AGENT.md の description に「対象外」節がない場合、SubAgentRegistry のロード時に警告ログを出力する
- [ ] **ROUTING-02**: RouterNode が2段構成（キーワード前段フィルタ → LLM）で動作し、50エージェント規模でもプロンプトサイズと精度が両立できる
- [ ] **ROUTING-03**: ルーティング結果が構造化ログ（input / chosen / candidates / correlation_id）に記録され、ミスルーティング分析が可能になる

### CONTEXT — RPCContext 統合

- [x] **CONTEXT-01**: RPCContext（user_id / app_id / thread_id / correlation_id）が AgentState のフィールドとして統合され、全ノードから state["context"] で参照できる
- [x] **CONTEXT-02**: RPCContext が frozen=True データクラス + _keep_first reducer により、グラフ実行中にノードが上書きできない
- [x] **CONTEXT-03**: HTTP リクエスト（from_http）と Slack イベント（from_slack）から RPCContext を構築するファクトリメソッドが利用できる
- [ ] **CONTEXT-04**: ルーティングログ・監査ログに correlation_id が含まれ、1リクエストの処理を横断追跡できる

### TOOL — ツール品質標準

- [ ] **TOOL-01**: フォルダ型エージェントのツールスクリプトに INPUT_SCHEMA 定数を定義することで、ツールのインターフェースが明示される
- [ ] **TOOL-02**: ScriptBackend がツール呼び出し前に INPUT_SCHEMA で入力値を jsonschema 検証し、不正入力を早期検出できる
- [ ] **TOOL-03**: scripts/lint_tools.py が CI で全ツールの INPUT_SCHEMA 欠落を自動検出し、新規エージェント追加時の品質ゲートになる

---

## Future Requirements

- REGISTRY-05: retry_ready() で再起動なしに DEGRADED → HEALTHY への回復を試みる（v3.1 候補）
- ROUTING-04: ルーティングログを蓄積・集計してミスルーティング率をダッシュボード表示（v3.1 候補）
- CONTEXT-05: 監査ログ（DB）に correlation_id を記録してクエリで追跡できる（v3.1 候補）
- TOOL-04: INPUT_SCHEMA を Anthropic API tools フォーマットへ自動変換、LLM がツールを直接呼び出せる（v4.0 候補 — tool calling 実装フェーズ）

## Out of Scope

- Slack ボット実装 — from_slack ファクトリを用意するが、Slack 連携は v3.0 では実装しない
- ツール呼び出し（LLM function calling） — INPUT_SCHEMA の構造は準備するが、bind_tools 実装は v4.0 以降
- エージェント間の非同期並列実行 — 現状は逐次ルーティング、並列化は v3.1 以降
- エージェント管理 UI（追加・削除・設定） — CLI / ファイル操作で管理、GUI は対象外

---

## Traceability

| REQ-ID | Phase | Plan |
|--------|-------|------|
| CONTEXT-01 | Phase 11 | — |
| CONTEXT-02 | Phase 11 | — |
| CONTEXT-03 | Phase 11 | — |
| CONTEXT-04 | Phase 11 | — |
| REGISTRY-01 | Phase 12 | — |
| REGISTRY-02 | Phase 12 | — |
| REGISTRY-03 | Phase 12 | — |
| REGISTRY-04 | Phase 12 | — |
| TOOL-01 | Phase 12 | — |
| TOOL-02 | Phase 12 | — |
| TOOL-03 | Phase 12 | — |
| ROUTING-01 | Phase 13 | — |
| ROUTING-02 | Phase 13 | — |
| ROUTING-03 | Phase 13 | — |
| APP-01 | Phase 14 | — |
| APP-02 | Phase 14 | — |
| APP-03 | Phase 14 | — |
| APP-04 | Phase 14 | — |
