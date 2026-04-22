# Phase 37: ファイル入力 — PDF/Office 抽出 + MCP ツール参照 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 37-pdf-office-mcp
**Areas discussed:** フォルダ規約・ライフサイクル / 抽出ライブラリ・対応フォーマット / 抽出処理の実行箇所 + LLM 注入 / MCP ツール設計 / 失敗ハンドリング

---

## Area 0: Gray area selection

| Option | Description | Selected |
|--------|-------------|----------|
| フォルダ規約・ライフサイクル | パス階層・命名・ボリューム・TTL・ADR 化 | ✓ |
| 抽出ライブラリ・対応フォーマット | 個別 / 統合・OCR・サイズ上限 | ✓ |
| 抽出処理の実行箇所 + LLM 注入方式 | 事前抽出 / LangGraph ノード / MCP on-demand・SystemMessage vs HumanMessage | ✓ |
| MCP ツールからのファイル参照方式 | volume mount / thread 解決 / 新規ツール要否 | ✓ |

**失敗ハンドリングサブ問**: 「まとめて決める」を選択 → Area 5 として追加。

---

## Area 1: フォルダ規約・ライフサイクル

### Q1-1: 共有フォルダのパス階層

| Option | Description | Selected |
|--------|-------------|----------|
| thread_id 単位フラット | `/shared/thread-files/<thread_id>/foo.pdf` — ROADMAP 指定、user 分離は thread_labels で論理保証 | |
| user_id/thread_id の 2 階層 | `/shared/thread-files/<github_login>/<thread_id>/foo.pdf` — ファイルシステムレベルで user 分離が視認可能 | ✓ |
| workspaces フラット | `/shared/workspaces/<thread_id>/{inputs,outputs}/` — Phase 38 と規約統合 | |

**User's choice:** user_id/thread_id の 2 階層

### Q1-2: ファイル名規則

| Option | Description | Selected |
|--------|-------------|----------|
| オリジナル名 + 衝突 suffix | `foo.pdf` / `foo (1).pdf` — ユーザーに分かりやすい | |
| タイムスタンプ prefix + オリジナル名 | `20260421T120000_foo.pdf` — 時系列で ls、衝突なし | ✓ |
| ハッシュ変換 | `sha1(content)[:12].pdf` — dedup 可、視認性×  | |

**User's choice:** タイムスタンプ prefix + オリジナル名

### Q1-3: 掃除と TTL

| Option | Description | Selected |
|--------|-------------|----------|
| thread 削除同期で rm -rf | `adelete_thread()` hook で folder 削除、TTL なし | ✓ |
| thread 削除 + 30 日 TTL | worker cron で TTL 掃除追加 | |
| 手動掃除のみ | 削除もしない MVP | |

**User's choice:** thread 削除同期で rm -rf

### Q1-4: Docker named volume 構成

| Option | Description | Selected |
|--------|-------------|----------|
| 新規 thread-files volume | claude-code-outputs とは独立 (Recommended 初案) | ✓ |
| claude-code-outputs に相乗り | volume は 1 本 | |
| ホスト bind mount | 開発時にホストから直接見える、本番不安定 | |

**User's choice:** 新規 thread-files volume

### Q1-4b: Volume mount の修正 (claude 側から指摘)

削除は API コンテナで走るため mount 構成を修正:

| Option | Description | Selected |
|--------|-------------|----------|
| api: RW / mcp-server: RO / worker: なし | 最小権限分割 (Recommended 初案) | |
| api: RW / mcp-server: RO / worker: RO | 将来 worker scan に向けた RO 保持 | |
| api: RW / mcp-server: RW / worker: RO | mcp-server にも RW (派生ファイル・将来 delete tool) | ✓ |

**User's choice:** api: RW / mcp-server: RW / worker: RO

**Notes:** Claude が「削除は API 側」と気づいて option 提示を訂正。ユーザーはさらに mcp-server を RW に拡張する選択で柔軟性を優先。

---

## Area 2: 抽出ライブラリ・対応フォーマット

### Q2-1: 抽出ライブラリの構成

| Option | Description | Selected |
|--------|-------------|----------|
| 個別ライブラリ併用 (pypdf + python-docx + openpyxl + python-pptx) | 軽量・OS パッケージ不要、abstraction 自作 (Recommended 初案) | |
| MarkItDown (Microsoft) 統合 | 1 lib で 4 フォーマット、LLM 向け Markdown 出力 | ✓ (free text "MarkItDownをDockerで使おうか。") |
| unstructured 統合 | 広範囲対応だが image +500MB | |

**User's choice:** MarkItDown (Other 経由の free text)

### Q2-2: OCR 対応

| Option | Description | Selected |
|--------|-------------|----------|
| 対応しない | スキャン PDF は extract 0 文字として返す、image 肥大なし (Recommended) | ✓ |
| pytesseract 導入 | image +200MB、ビルド遅延 | |

**User's choice:** 対応しない

### Q2-3: サイズ上限と対応拡張子

| Option | Description | Selected |
|--------|-------------|----------|
| 25 MB / MS 4 フォーマット | GitHub attachment サイズ同等 (Recommended 初案) | |
| 100 MB / MS + ODF 拡張 | LibreOffice 必要 | ✓ |
| 50 MB / MS + text/code | Phase 36 先行取り込み | |

**User's choice:** 100 MB / pdf docx xlsx pptx + odt ods odp

### Q2-3b: ODF 対応と MarkItDown のギャップ解消

| Option | Description | Selected |
|--------|-------------|----------|
| ODF は落として MS のみ | image ミニマル (Recommended 初案) | ✓ |
| libreoffice CLI 導入で ODF→MS 変換 | image +200-300MB | |
| odfpy で ODF 並行対応 | abstraction 自作 | |

**User's choice:** ODF は落として MS のみ

**Notes:** MarkItDown が ODF 非対応のため、Q2-3 の「100MB/MS+ODF」をそのまま採用できず整合確認。ユーザーは image 軽量を優先し ODF 除外を選択。最終: 100MB, pdf/docx/xlsx/pptx のみ。

---

## Area 3: 抽出処理の実行箇所 + LLM 注入方式

### Q3-1: 抽出箇所

| Option | Description | Selected |
|--------|-------------|----------|
| worker handler で事前抽出 | 初回 handler で scan + SystemMessage 注入 (Recommended 初案) | |
| LangGraph ノードとして組み込み | ExtractFilesNode で trace に乗る | |
| 新規 MCP ツールで on-demand 抽出 | agent が呼んだときだけ抽出、prompt 膨張最小 | ✓ |

**User's choice:** 新規 MCP ツールで on-demand 抽出

### Q3-2: LLM 注入方式

| Option | Description | Selected |
|--------|-------------|----------|
| SystemMessage 先頭注入 + state 保持 | 抽出済みを prepend (Recommended 初案) | ✓ |
| HumanMessage に添付として埋め込み | 自然な会話履歴だが重複懸念 | |
| state にだけ保持、MCP tool で読む | token 節約だが呼び忘れリスク | |

**User's choice:** SystemMessage 先頭注入 + state 保持

### Q3-3: 文字数上限

| Option | Description | Selected |
|--------|-------------|----------|
| 1 ファイル 50K / 合計 200K、超過 truncate + 警告 (Recommended) | 128-200K context window に収まる範囲 | ✓ |
| 1 ファイル 100K / 合計 300K | 大容量前提、200K モデルは埋まる | |
| 上限なし、model エラーをそのまま返す | MVP simple | |

**User's choice:** 1 ファイル 50K / 合計 200K、超過 truncate + 警告

### Q3-4: Q3-1 と Q3-2 の矛盾解消 (claude 側から指摘)

「on-demand 抽出」と「先頭注入」は通常両立しないため 3 択で再確認:

| Option | Description | Selected |
|--------|-------------|----------|
| ハイブリッド: 添付一覧のみ SystemMessage、内容は MCP tool で on-demand | agent がファイル存在を認識しつつ内容は tool 経由で取得 (Recommended) | ✓ |
| 事前抽出 → SystemMessage に全文 | Q3-1 を option 1 に訂正 | |
| 事前抽出 + SystemMessage + MCP tool でも再抽出可 | 両方 (冗長) | |

**User's choice:** ハイブリッド (添付一覧のみ SystemMessage、内容は MCP tool で on-demand)

**Notes:** Q3-1 と Q3-2 の選択が両立しないため claude が再確認。ハイブリッド案で決着。一覧メタデータだけ prepend、本文は `attachments_extract` で都度取得する設計に。

---

## Area 4: MCP ツール設計 + volume mount + thread 分離

### Q4-1: ツール粒度

| Option | Description | Selected |
|--------|-------------|----------|
| attachments_list + attachments_extract の 2 本 (Recommended) | 役割明確、一覧 → 必要分だけ extract | ✓ |
| attachments_extract 1 本に merge | 引数なしで全、filename 指定で 1 件 | |
| list + extract + read_bytes の 3 本 | バイナリ読みたいとき用、YAGNI 気味 | |

**User's choice:** attachments_list + attachments_extract の 2 本

### Q4-2: Volume mount 初回

| Option | Description | Selected |
|--------|-------------|----------|
| mcp-server のみ RW、worker は RO (Recommended 初案) | 最小権限 | ✓ (一旦) |
| mcp-server と worker 両方 RW | 将来 MCP tool 書き込みに備える | |
| worker と execute_python sandbox にも mount | sandbox から open() 可 | |

**User's choice (初回):** mcp-server のみ RW、worker は RO

(後に Q1-4b で「api 側で削除が走る」ことを claude が指摘し再質問 → 最終 api RW / mcp-server RW / worker RO に修正)

### Q4-3: thread 解決

| Option | Description | Selected |
|--------|-------------|----------|
| RPCContext 経由で mcp-server 側で解決 (Recommended) | LLM は filename のみ渡す、cross-thread 遮断 | ✓ |
| tool 引数で thread_id を受け取る | シンプルだが越境リスク | |
| 両方、RPCContext を authoritative | 冗長 | |

**User's choice:** RPCContext 経由で mcp-server 側で解決

---

## Area 5: 抽出失敗時のハンドリング

### Q5-1: エラーカテゴリ

| Option | Description | Selected |
|--------|-------------|----------|
| 5 種 (password / corrupt / size_over / unsupported / extract_timeout) (Recommended) | 分類細かく、observability で分析可 | ✓ |
| 3 種 (generic / size_over / unsupported) | シンプル | |
| 2 値 (success / failed) | 最小実装 | |

**User's choice:** 5 種

### Q5-2: 失敗と truncate 警告の伝達

| Option | Description | Selected |
|--------|-------------|----------|
| MCP tool の戻り値に error フィールド (Recommended) | `{content, error, truncated, truncated_chars}` 構造化、web_search パターン | ✓ |
| attachments_list に extractable フラグ追加 | list の probe 負荷 | |
| content に文字列として混ぜる | 判別が文字列 match 依存 | |

**User's choice:** MCP tool 戻り値に error フィールド

### Q5-3: 再試行

| Option | Description | Selected |
|--------|-------------|----------|
| 再試行ロジックなし — agent 判断 (Recommended) | シンプル、timeout も tool 戻り値で通知 | ✓ |
| transient error で 1 回 auto retry | 安定化、複雑化 | |

**User's choice:** 再試行ロジックなし

---

## Claude's Discretion

- ADR 本文の書き振り (具体パス例の数、Phase 36/38 との接続 interface 記述粒度)
- Docker Compose の volume 定義書式・bind mount との切り替え可能性
- `attachments_list` の戻り値追加フィールド (MIME type・ハッシュ等)
- SystemMessage テンプレート文言
- MarkItDown の実行方式 (subprocess vs in-process)
- MarkItDown pin バージョン
- 抽出キャッシュ層の要否
- execute_python sandbox allowlist に MarkItDown import を追加するか

## Deferred Ideas

- Phase 36 アップロード UI / API (別 phase scope)
- Phase 38 ユーザー別永続ストレージ (別 phase scope、規約のみ共通化)
- OCR 対応 (v6.1+)
- ODF (odt/ods/odp) 対応 (v6.1+)
- attachments_read_bytes バイナリ tool (YAGNI)
- 抽出結果キャッシュ層 (Phase 39 / v6.1 で observability 観察後)
- 抽出失敗の UI エラー表示 (Phase 36 責務)
- マルチモーダル画像入力 (Phase 36 責務、FIN-02)
