# 0048. thread-files 共有フォルダ規約 (Phase 37)

**Status:** Accepted
**Date:** 2026-04-21
**Phase:** 37 — ファイル入力 — PDF/Office 抽出 + MCP ツール参照
**Supersedes:** なし
**Related ADRs:** [0020](0020-fastmcp-docker-service-infrastructure.md), [0023](0023-mcp-db-query-and-claude-code-tools.md), [0026](0026-thread-deletion-also-removes-threads-table-row.md), [0044](0044-mcp-tool-catalog-single-source-of-truth.md)

## Context

Phase 37 で PDF/Office ファイルの添付機能を実装するにあたり、以下を満たすフォルダ規約が必要になった:

- ユーザー分離 (200 名規模・マルチユーザー運用)
- thread 単位のライフサイクル (thread 削除で添付も消える、TTL/cron 不要)
- api / mcp-server / worker の 3 サービス間で共有アクセス (worker は RO)
- Phase 36 (アップロード UI) と Phase 38 (出力ストレージ) が同じ規約で接続できる

先例として ADR-0023 の `claude-code-outputs` named volume (mcp-server: RW / worker: RO の 2 サービスマウント) と ADR-0026 のスレッド削除原子性パターンがある。本 ADR はこれらを拡張してユーザー分離階層とライフサイクル hook を加えた規約を定める。

## Decision

### パス階層

`/shared/thread-files/<github_login>/<thread_id>/` の 2 階層とする。

- `github_login` は JWT payload から取得 (API 既存パターン、Phase 11-04 以降で確立)
- `thread_id` は既存 LangGraph スレッド ID と同一値
- `THREAD_FILES_DIR` 環境変数で base path を上書き可能 (テスト時の tmpdir 差し替え)

例:
```
/shared/thread-files/
  octocat/
    thread_abc123/
      20260421T120000_report.pdf
      20260421T121500_data.xlsx
    thread_def456/
      20260421T133000_slide.pptx
```

### ファイル命名

`YYYYMMDDTHHMMSS_<original_name>.<ext>` (UTC タイムスタンプ prefix)。

- 衝突は timestamp prefix で回避
- `ls` で時系列並び保証
- LLM にはオリジナル名ベースで見せる (prefix は実装詳細)

### ライフサイクル

「thread 削除と同期」。`app/api/routes/chat.py::delete_thread` が
`checkpointer.adelete_thread(thread_id)` 直後に realpath prefix guard を通したうえで
`shutil.rmtree(thread_folder, ignore_errors=True)` を呼ぶ。

TTL / cron による自動削除は設けない。

### Docker volume 構成

`thread-files` named volume (`claude-code-outputs` と独立)。

| サービス | mount | 理由 |
|---------|-------|------|
| api | RW | 削除 + 将来のアップロード書き込み |
| mcp-server | RW | 抽出時の派生ファイル書き出し余地 |
| worker | RO | scan のみ。書き込み禁止で攻撃経路遮断 |

docker-compose.yml の volumes セクション構成例:
```yaml
volumes:
  thread-files:

services:
  api:
    volumes:
      - thread-files:/shared/thread-files
  mcp-server:
    volumes:
      - thread-files:/shared/thread-files
  worker:
    volumes:
      - thread-files:/shared/thread-files:ro
```

### 抽出失敗時の挙動 (D-08) — テキスト 0 文字 PDF の扱い

MarkItDown でテキスト抽出が 0 文字になる PDF (スキャン PDF / 画像のみ PDF 等) は、
**`error` を返さず `content: ""` + メタ情報 (`truncated: false, truncated_chars: 0, filename: ...`)
を返す**。意図は次の通り:

- LLM がこの結果を受け取り、ユーザーに対して「この PDF からはテキストを抽出できなかった。
  OCR が必要な可能性がある。ファイルはアップロード済みだがテキストが読めない」旨を
  自然言語で説明できる状態を保つ
- `unsupported` / `corrupt` エラーコードとは明確に区別する (フォーマットや破損ではなく、
  「テキスト情報が存在しない有効な PDF」というシグナルを残す)
- OCR 対応は v6.1+ に deferred (D-08)

戻り値の例:
```json
{
  "content": "",
  "error": null,
  "truncated": false,
  "truncated_chars": 0,
  "filename": "20260421T120000_scan.pdf"
}
```

### Path traversal 対策

`attachments_extract` MCP ツールの `filename` 引数は basename のみを受け付ける。
mcp-server 側で以下を実施:

```python
safe_path = os.path.realpath(os.path.join(thread_folder, filename))
assert safe_path.startswith(os.path.realpath(thread_folder) + os.sep)
```

これにより `../../../etc/passwd` 等の path traversal を防ぐ。delete_thread hook でも同様の realpath guard を通す。

### Phase 36 / Phase 38 との接続契約

- **Phase 36 (入力 UI)**: アップロードエンドポイントは書き込み先を `THREAD_FILES_DIR/<github_login>/<thread_id>/`
  に固定し、ファイル命名規則 `YYYYMMDDTHHMMSS_<original>.<ext>` を踏襲する
- **Phase 38 (出力ストレージ)**: 本 ADR と別 volume にするか同一 volume にサブディレクトリを切るかは
  Phase 38 で決定。ユーザー別ストレージ (FOUT-04) の永続保持方針は Phase 37 の範囲外 (本 volume は thread 削除で消える)

## Consequences

### 良い点

- コード側は `THREAD_FILES_DIR` + `<login>/<tid>/` の 3 要素で一意に解決できる
- path traversal 対策は MCP ツール (`os.path.realpath` + prefix assert) + delete_thread hook
  (同様の realpath guard) に閉じ込められる
- 200 名 × 数十 thread × 数 MB/thread = 数 GB 規模の運用で volume 肥大化は許容範囲
- Phase 36 / Phase 38 の plan が本 ADR を canonical ref として参照できる
- テキスト 0 文字 PDF (D-08) は `content: ""` + `error: null` で返すため、LLM が原因をユーザーに説明できる

### 悪い点 / トレードオフ

- ODF ファイル / OCR / バイナリ読み出し tool は本 phase scope 外 (D-07/D-08/Deferred)
- 大容量ファイル (100 MB 超) は size_over エラーで拒否
- OS パッケージ (LibreOffice / tesseract) 追加はしない — image 肥大回避
- テキスト 0 文字 PDF は「成功扱いだが content が空」という特殊パス。
  LLM がこれを誤解釈 (「何も添付されていない」と応答) しないようプロンプト調整が必要

### 追加で決まったもの

- 抽出は on-demand (MCP tool `attachments_extract` 経由)。worker による事前抽出はしない (D-10)
- SystemMessage には一覧のみ prepend (本文は含めない) (D-11)
- RPCContext は HTTP ヘッダー経由で mcp-server 側が解決 — tool 引数に thread_id を含めない (D-17)

## 参考情報

- 先例: ADR-0023 `claude-code-outputs` shared volume + env sanitization パターン
- 先例: ADR-0026 thread 削除時の原子削除の思想
- 先例: ADR-0044 MCP カタログ SSoT (新規ツールの登録フロー)
- 先例: ADR-0020 FastMCP Docker サービス基盤 (streamable-http transport)
