# Phase 37: ファイル入力 — PDF/Office 抽出 + MCP ツール参照 - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

サーバー側で PDF / Office ファイル (docx / xlsx / pptx) をテキスト抽出し、thread_id 単位の共有フォルダ規約を確立して、同じファイルを MCP ツール (`execute_python` / `claude_code` / 新規 `attachments_*`) から参照できる基盤を構築する。

**scope 前提 (2026-04-21 調整 / commit 91fface):**
- Phase 36 のアップロード UI は待たない。ファイルは共有フォルダに事前配置される前提で抽出パイプラインと MCP 参照を実装する。
- フォルダ規約は **ADR 化し**、Phase 36 (入力 UI) と Phase 38 (出力 — ユーザー別ストレージ) が同じ規約で後から接続できるようにする (success criteria 5)。
- アップロード UI・ダウンロード UI・UI エラー表示は Phase 36 / 38 の責務。本 phase は抽出パイプラインと MCP 参照契約で閉じる。

</domain>

<decisions>
## Implementation Decisions

### フォルダ規約・ライフサイクル (ADR 化対象)

- **D-01:** 共有フォルダのパス階層は `/shared/thread-files/<github_login>/<thread_id>/` の 2 階層とする。github_login は JWT payload から取得、thread_id は既存 LangGraph スレッド ID と同一値を使う。
- **D-02:** ファイル命名規則は `YYYYMMDDTHHMMSS_<original_name>.<ext>` とする。衝突は timestamp prefix で回避され、`ls` が時系列で並ぶ。LLM にはオリジナル名ベースで見せる。
- **D-03:** ライフサイクルは「thread 削除と同期」。API コンテナの `app/api/routes/chat.py::delete_thread` (既存 `adelete_thread()` 呼び出し箇所) に hook を追加し、フォルダを `rm -rf` する。TTL や cron による自動削除はしない。
- **D-04:** Docker named volume は `thread-files` を **新規作成** する (既存 `claude-code-outputs` とは独立)。mount 構成は **api: RW / mcp-server: RW / worker: RO**。api は削除 + 将来のアップロード書き込みで RW、mcp-server は抽出 + 将来の派生ファイル書き出しに備えて RW、worker は触らないが RO mount は保持 (将来の scan 用途に向けた安全側の既定)。
- **D-05:** フォルダ規約 (パス / 命名 / mount / ライフサイクル) は本 phase で ADR 化する (success criteria 5)。ADR 番号は次の空き番を取り、`.planning/patterns.md` にも「Data・Persistence」カテゴリで 1 エントリ追記する。

### 抽出ライブラリ・対応フォーマット

- **D-06:** 抽出ライブラリは **MarkItDown (Microsoft)** を単独採用する。pip 依存のみで Docker image に追加 (LibreOffice / tesseract 等の OS パッケージは追加しない)。
- **D-07:** 対応フォーマットは `.pdf / .docx / .xlsx / .pptx` の 4 つに限定する。.odt / .ods / .odp 等 ODF 系は本 phase では非対応 (MarkItDown が直接対応しないため、LibreOffice 等の OS パッケージ追加が必要になり image 肥大のコスパが合わない)。社内は Office 365 主流との前提。
- **D-08:** OCR (スキャン PDF) は非対応とする。テキスト抽出が 0 文字の PDF は `unsupported` エラーではなく `content: ""` + メタ情報を返し、LLM がその事実をユーザーに説明できるようにする。v6.1+ でユーザー要求が高まったら再検討。
- **D-09:** 1 ファイルあたりのサイズ上限は **100 MB**。超過は抽出前に `size_over` エラーで拒否 (MarkItDown を起動しない)。

### 抽出処理の実行箇所 + LLM 注入

- **D-10:** 抽出は **MCP tool 経由の on-demand 実行** とする。worker handler や LangGraph node での事前抽出はしない。agent が必要なときだけ `attachments_extract` を呼ぶ。
- **D-11:** worker handler (例: `langgraph_handler.py`) は LangGraph 実行開始前に thread フォルダを scan し、**添付一覧 (ファイル名・サイズ・タイムスタンプ) だけ** を SystemMessage として `messages[0]` に prepend する。content 本体は含めない。hint として "内容を読むには attachments_extract MCP tool を呼ぶこと" の指示も同 SystemMessage に入れる。
- **D-12:** AgentState に `attachments: list[dict]` フィールドを追加し、scan 結果のメタデータを state に保持する。checkpoint 経由で再オープン時も復元される。LangGraph の reducer は追加ではなく置換 (last-writer-wins) で良い — handler が毎 turn scan する。
- **D-13:** 抽出テキストの上限は **1 ファイル 50,000 文字 / 1 スレッド 200,000 文字**。超過は末尾を truncate し、tool 戻り値の `truncated: true, truncated_chars: N` で LLM に通知する。合計上限は同 turn 内の extract 呼び出しをトラッキングする必要があるかは planner に委ねる (セッション内合算で十分か、state に書くかは実装側判断)。

### MCP ツール設計 (Phase 30 SSoT 経由で登録)

- **D-14:** 新規 MCP ツールは **2 本**:
  - `attachments_list`: 引数なし (thread は RPCContext 解決)、戻り値 `[{name, size, modified_at, ext}, ...]`
  - `attachments_extract`: 引数 `filename: str`、戻り値 `{content: str | null, error: {code, message} | null, truncated: bool, truncated_chars: int, filename: str}`
- **D-15:** ツール登録は `/add-mcp-tool` スラッシュコマンド経由で行い、`config/mcp_tools.yaml` を唯一のソースとする (Phase 30 ADR-0044)。`scripts/generate_mcp_artifacts.py --target all` で `mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md` を再生成、pre-commit hook で drift 検知する。
- **D-16:** 両ツールとも **`privileged: false`**、**`sandbox_exposed: true`**。execute_python sandbox からも mcp_helper 経由で呼べるようにする (agent が CodeAct で attach 内容を参照・解析できる)。
- **D-17:** thread 解決は **RPCContext 経由** で mcp-server 側が行う。LLM (agent) は `thread_id` を tool 引数として渡さない。mcp-server は MCP セッションに紐づく RPCContext (`thread_id` / `github_login`) からフォルダパスを構築する。これにより悪意あるプロンプト / プロンプト汚染で他 thread を読まれる経路を遮断する (ADR 化でもこの原則を明記)。
- **D-18:** `attachments_extract` の `filename` 引数は basename のみを受け付け、mcp-server 側で `os.path.realpath` 後に thread フォルダの prefix を assert する (path traversal 対策)。

### 失敗ハンドリング

- **D-19:** 抽出エラーは **5 カテゴリ構造化**:
  - `password`: password 保護された PDF / Office
  - `corrupt`: ファイル破損 / MarkItDown 内部例外
  - `size_over`: 100 MB 超過 (抽出前チェックで拒否)
  - `unsupported`: 拡張子が D-07 の 4 種以外 / MarkItDown がサポート外と判定
  - `extract_timeout`: 60 秒でタイムアウト (claude_code と同じ値)
- **D-20:** 失敗・truncate は `attachments_extract` 戻り値の構造化フィールドで返す (`error: {code, message}`、`truncated: bool` 等、D-14 参照)。例外は raise しない。web_search の `[{error: "..."}]` 形式を参考にした非例外フローで、LLM は自然言語で原因をユーザーに伝える。
- **D-21:** 再試行ロジックは MCP tool 側には持たない。agent が必要と判断したら再呼び出しする。`extract_timeout` が transient な場合の retry は agent のプロンプト次第。observability で頻度が目立ったら Phase 39 polish / v6.1 で再検討。

### Claude's Discretion

- ADR 本文の書き振り (具体パス例の数、Phase 36/38 との接続 interface 記述粒度)
- Docker Compose の volume 定義書式・bind mount との切り替え可能性
- `attachments_list` の戻り値追加フィールド (MIME type・ハッシュ等は必要なら追加)
- SystemMessage のテンプレート文言 (日本語・英語の使い分け・"このファイルは以下のツールで..." のような hint 記述)
- MarkItDown の subprocess 実行 vs in-process 呼び出し (image サイズと timeout 制御の影響)
- MarkItDown pin バージョン (pyproject.toml で exact pin するか `>=` にするか)
- Thread state に抽出キャッシュを持たせるかどうか (on-demand 原則に反しない範囲で)
- execute_python sandbox allowlist に MarkItDown 直接 import を追加するか (D-16 により mcp_helper 経由で呼べるなら不要)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 37 要件

- `.planning/ROADMAP.md` §Phase 37 — Goal / Depends / Success Criteria 1-5 (scope 調整 2026-04-21 の脚注含む)
- `.planning/REQUIREMENTS.md` — FIN-03 (PDF/Office 抽出) / FIN-04 (MCP ツール参照)

### パターンカタログ (必須参照 — CLAUDE.md 運用ルール)

- `.planning/patterns.md` — ADR 由来パターンカタログ。今回追加するフォルダ規約も本ファイルに追記する (D-05, D-15)
- `docs/adr/INDEX.md` — ADR カテゴリ別索引

### MCP ツール追加フロー (Area 4 の要所)

- `docs/adr/0020-fastmcp-docker-service-infrastructure.md` — FastMCP Docker サービス・streamable-http transport
- `docs/adr/0023-mcp-db-query-and-claude-code-tools.md` — shared volume (claude-code-outputs) 前例、env sanitization
- `docs/adr/0024-mcp-tool-catalog-validation.md` — ToolRegistry 整合性検証
- `docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md` — YAML SSoT + ジェネレータ + drift 検知 (ツール追加の必須フロー)
- `docs/mcp-tool-add-manual.md` — 新規ツール追加の手順書
- `config/mcp_tools.yaml` — ツール宣言スキーマと既存 6 ツール例 (`ping`, `web_search`, `db_query`, `execute_python` 等)
- `CLAUDE.md` §"MCP Tool Catalog (Phase 30)" — 手書きと自動生成ファイルの境界

### Observability / trace 統合

- `docs/adr/0045-phase-31-observability-jsonl.md` — stdout JSONL / trace_id = RPCContext.correlation_id、新規ツールも同形式で span を出す
- `docs/trace-query-recipes.md` — 検証時のクエリ例

### LLM / LangGraph 周り (Area 3 の SystemMessage 注入)

- `docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md` — AIMessage / SystemMessage を LangGraph checkpoint で保持するときの注意
- `docs/adr/0041-codeact-direct-execution-over-react.md` — execute_python 直接実行方式 / sandbox 思想 (D-16 の sandbox_exposed 設定の前提)
- `docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md` — SystemMessage 注入の既存パターン
- `app/orchestrator/state.py` — AgentState 定義 (D-12 で `attachments` フィールドを追加する対象)
- `app/jobs/handlers/langgraph_handler.py` — worker handler の既存挙動 (D-11 で scan + SystemMessage 注入を追加する場所)

### ライフサイクル hook (Area 1)

- `docs/adr/0026-thread-deletion-also-removes-threads-table-row.md` — thread 削除時の原子削除の思想 (D-03 の rm -rf hook と整合)
- `app/api/routes/chat.py::delete_thread` (line 346-382 付近) — `adelete_thread()` 呼び出し直後に folder rm hook を足す対象

### 既存 sandbox / shared volume 前例

- `mcp_server/tools/claude_code.py` — `/shared/claude-code-outputs/` への大型出力書き出し / env allowlist の先例 (D-19 `extract_timeout` 60 秒は D-03 の TIMEOUT_SECS と同値)
- `mcp_server/tools/execute_python.py` — AST allowlist / env allowlist / メモリ制限 (D-16 で mcp_helper 経由呼び出しの前例)
- `mcp_server/tools/web_search.py` — エラーを例外ではなく戻り値 `{error: "..."}` で返すパターン (D-20 の構造化エラー設計の手本)
- `docker-compose.yml` — 既存 `claude-code-outputs` named volume 定義 (D-04 の `thread-files` 新規 volume の定義書式はこれを流用)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **RPCContext** (`app/orchestrator/context.py`): `thread_id` / `github_login` / `correlation_id` を frozen dataclass で保持。MCP tool 呼び出し時に mcp-server 側で取得できれば D-17 が成立する。MCP session から RPCContext をどう渡すかは planner / researcher が決める (FastMCP context / ヘッダー / seed tool call 等)。
- **`claude-code-outputs` named volume** (docker-compose.yml): shared volume のパターン先例 — `thread-files` volume も同じ書式で追加可能。
- **`app/api/routes/chat.py::delete_thread`** (line 346-382): 既存の `adelete_thread()` 呼び出し直後に folder rm hook を足すだけで D-03 が実現する。
- **`mcp_server/tools/web_search.py`**: 戻り値の `error` フィールドパターンは D-20 の設計にそのまま使える。
- **`scripts/generate_mcp_artifacts.py`** + **`/add-mcp-tool` skill**: D-15 のツール登録フロー (YAML 変更 → 再生成 → pre-commit drift check) がすべて既存。

### Established Patterns
- **config/mcp_tools.yaml single source of truth** (ADR-0044): 新規ツール追加は YAML + `--target all` 再生成のみ。手で mcp_helper.py / js カタログ / docs を編集しない。
- **Privileged vs sandbox-exposed**: `privileged: true` は SubAgentRegistry が警告、`sandbox_exposed: false` は mcp_helper に wrapper 生成しない (execute_python sandbox 内部から呼べなくなる)。D-16 は両方 false/true で合っているか planner に最終確認させる。
- **SystemMessage prepend in LangGraph**: ADR-0025 で datetime / github_login を SystemMessage に注入する既存パターンあり。D-11 の添付一覧 prepend も同じ箇所 (system prompt builder 側) で行うと自然。
- **JWT payload based github_login 伝搬**: `github_login` は JWT → arq job payload → RPCContext と既に伝搬済み (Phase 11-04)。D-01 のフォルダパス解決に新たな配線は要らない。

### Integration Points
- **docker-compose.yml**: `volumes:` に `thread-files` named volume を追加、`api` / `mcp-server` / `worker` の `volumes:` セクションに mount 行を追加。
- **pyproject.toml (worker 側)** と **mcp_server/requirements** (mcp-server 側): MarkItDown は mcp-server 側にだけ入れれば足りる (抽出は mcp-server で走るため)。worker の pyproject.toml には追加不要。
- **`config/mcp_tools.yaml`**: `tools:` 配列末尾に `attachments_list` / `attachments_extract` の 2 エントリを追加し `scripts/generate_mcp_artifacts.py --target all` を実行。
- **`app/orchestrator/state.py`** (AgentState TypedDict): `attachments: list[dict]` を追加。
- **`app/jobs/handlers/langgraph_handler.py`**: thread フォルダ scan + SystemMessage 構築ロジックを追加。
- **`app/api/routes/chat.py::delete_thread`**: folder rm hook を `await checkpointer.adelete_thread(thread_id)` の直後に足す。

</code_context>

<specifics>
## Specific Ideas

- **MarkItDown を選んだ理由**: LLM 向けに正規化された Markdown を返すので、生 PDF テキストより LLM が構造を掴みやすい。社内 200 名規模には OS パッケージ依存のない pip 一本で済むのが最大の利点。ODF 対応を切った判断とセット。
- **失敗は例外ではなく戻り値で返す**: web_search のパターンを踏襲。LLM はエラーメッセージを自然言語でユーザーに伝える責任を持つ — 「password 保護されているのでパスワード解除版をアップロードしてください」のようなガイダンスを含むレスポンスを期待する。
- **thread_id は tool 引数で受け取らない**: プロンプト汚染 (「別の thread のファイルを見せろ」とユーザーが言えてしまう経路) を遮断するための設計判断。mcp-server 側で RPCContext から解決することが ADR の核心の 1 つ。
- **worker を RO で mount する理由**: 現状 worker は thread-files を触らないが、将来「handler で scan してメタデータを state に書く」動線で RO は欲しい。RW にする合理性がないので RO 固定。

</specifics>

<deferred>
## Deferred Ideas

- **Phase 36 のアップロード UI / API**: 本 phase の scope 外。Phase 36 は本 phase で確立する `/shared/thread-files/<github_login>/<thread_id>/` フォルダ規約に書き出すだけで繋がる。
- **Phase 38 の生成ファイル保持・ダウンロード UI**: 本 phase で規約は共通化するが、ユーザー別ストレージ (FOUT-04) の永続保持方針は Phase 38 で別途決定する (本 phase は thread 削除で消える一時ストレージのみ)。
- **OCR (スキャン PDF 対応)**: D-08 で非対応と決定。v6.1+ でユーザー要望が強まれば検討。
- **ODF (odt/ods/odp) 対応**: D-07 で非対応と決定。LibreOffice CLI の image 肥大とコスパが合わない。v6.1+ で要望次第。
- **バイナリ読み出し tool (attachments_read_bytes)**: 現時点では volume mount + execute_python sandbox の直接 open() で十分のため追加しない。必要に迫られたら YAGNI を崩して追加。
- **抽出結果のキャッシュ層**: 同一ファイルを複数 turn で繰り返し extract する場合のキャッシュは、observability で頻度を見てから Phase 39 / v6.1 で検討。
- **UI エラー表示 (Phase 36 責務)**: 抽出失敗を UI で表示する際の見せ方は Phase 36 の UX スコープ。本 phase は LLM 経由でユーザーに伝達する設計で閉じる。
- **マルチモーダル画像 (Phase 36 責務)**: FIN-02 は Phase 36 で扱う。本 phase の抽出対象は PDF/Office のみ。

</deferred>

---

*Phase: 37-pdf-office-mcp*
*Context gathered: 2026-04-21*
