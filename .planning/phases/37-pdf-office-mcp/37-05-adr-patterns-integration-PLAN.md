---
phase: 37
plan: 05
type: execute
wave: 3
depends_on: ["37-03", "37-04"]
files_modified:
  - docs/adr/0048-thread-files-folder-convention.md
  - .planning/adr-categories.yaml
  - .planning/patterns.md
  - docs/adr/INDEX.md
  - docs/phase-37-integration-check.md
  - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md
autonomous: false
requirements: [FIN-03, FIN-04]
estimated_minutes: 60
tags: [adr, patterns, integration-check, docs]

must_haves:
  truths:
    - "フォルダ規約 (パス / 命名 / mount / ライフサイクル) が ADR-0048 として文書化されている (D-05, Success Criteria 5)"
    - "ADR-0048 に D-08 の方針 (テキスト 0 文字 PDF は error ではなく content:\"\" を返す) が明記されている (S-02 対応)"
    - "Phase 36 (アップロード UI) と Phase 38 (出力ストレージ) が同じ規約で接続できるよう interface が明記されている"
    - "`.planning/patterns.md` の Data・Persistence セクションに 1 エントリ追加されている (D-15)"
    - "`docs/adr/INDEX.md` に 0048 エントリが反映されている (pre-commit hook で自動再生成)"
    - "Integration check (実 docker compose 環境での 1 経路 end-to-end 動作) の観察結果が `docs/phase-37-integration-check.md` に残されている (ADR-0046 patterns)"
    - "VALIDATION.md の Per-Task Map が全 Wave (0/1/2/3) で埋まり、`nyquist_compliant: true` / `status: validated` に更新されている"
  artifacts:
    - path: "docs/adr/0048-thread-files-folder-convention.md"
      provides: "thread-files フォルダ規約の ADR 本文"
      contains: "/shared/thread-files"
      min_lines: 60
    - path: ".planning/patterns.md"
      provides: "Data・Persistence セクションに thread-files 規約の 1 エントリ追加"
      contains: "thread-files"
    - path: "docs/adr/INDEX.md"
      provides: "ADR 0048 エントリ (pre-commit hook で自動生成)"
      contains: "0048"
    - path: "docs/phase-37-integration-check.md"
      provides: "実環境での 1 経路 end-to-end 動作観察レポート"
      contains: "## 観察結果"
  key_links:
    - from: "docs/adr/0048-thread-files-folder-convention.md"
      to: ".planning/patterns.md (Data・Persistence)"
      via: "関連 ADR リンク + 手動追記"
      pattern: "0048-thread-files"
    - from: "docs/adr/INDEX.md"
      to: "docs/adr/0048-thread-files-folder-convention.md"
      via: "scripts/generate_adr_index.py (pre-commit hook)"
      pattern: "0048.*thread-files"
---

<objective>
Phase 37 の Success Criteria 5 (「フォルダ規約 (パス / 命名 / ライフサイクル) が ADR 化され、
Phase 36 と Phase 38 が同じ規約で接続できる」) を満たし、patterns.md 追記と INDEX 再生成を hook 経由で確定させる。
さらに Phase 31 で確立した `Integration check gate` (patterns.md) に従って、docker compose 環境で
end-to-end 1 経路を実際に動かし、silent failure が無いことを確認する。

ADR-0048 には、CONTEXT.md D-08 で決めた「テキスト抽出 0 文字の PDF は error ではなく `content: ""` を
返して LLM がユーザーに説明可能にする」方針も明記する (S-02 対応)。

Purpose:
- Phase 36 / Phase 38 が本 phase の規約に乗れる形で文書を完結させる
- unit test green + integration check green の 2 ゲートで phase を閉じる

Output:
- ADR-0048 本文 (D-08 方針を含む)
- patterns.md への 1 エントリ追加
- docs/adr/INDEX.md の更新 (自動生成結果)
- docs/phase-37-integration-check.md
- VALIDATION.md の Wave 3 行追記 + frontmatter 最終化
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/37-pdf-office-mcp/37-CONTEXT.md
@.planning/phases/37-pdf-office-mcp/37-RESEARCH.md
@.planning/phases/37-pdf-office-mcp/37-VALIDATION.md
@.planning/phases/37-pdf-office-mcp/37-03-SUMMARY.md
@.planning/phases/37-pdf-office-mcp/37-04-SUMMARY.md
@.planning/patterns.md
@docs/adr/INDEX.md
@docs/adr/0023-mcp-db-query-and-claude-code-tools.md
@docs/adr/0026-thread-deletion-also-removes-threads-table-row.md
@docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md
@docs/adr/0046-integration-check-surfaced-silent-failures.md
@CLAUDE.md

<interfaces>
<!-- 既存 ADR のフロントマター形式 (参考: 0023, 0026, 0044) -->
- title (行頭 `# ADR-NNNN: ...`)
- Status / Date / Context / Decision / Consequences / Related ADRs セクション
- 関連 ADR へのリンクは相対パス `[0023](0023-mcp-db-query-and-claude-code-tools.md)` 形式

<!-- patterns.md の既存 `Data・Persistence` セクション末尾 (参考) -->
```markdown
### Stdout 1 行 JSONL による observability 永続化
...
関連 ADR: [0045](../docs/adr/0045-phase-31-observability-jsonl.md)
```

<!-- ADR INDEX 自動生成 -->
scripts/generate_adr_index.py が pre-commit hook で `docs/adr/NNNN-*.md` を検知して
`docs/adr/INDEX.md` を再生成する。`.planning/adr-categories.yaml` にカテゴリマッピングを追加する必要あり。

<!-- Integration check gate (ADR-0046) -->
「Phase 完了前に docker compose 実環境で 1 経路以上を end-to-end 手動 / 自動操作し、
 observe された実トレースを phase SUMMARY に貼付」パターンを踏襲する。
</interfaces>

<skills>
- `.claude/skills/create-adr` — ADR 作成 + INDEX 自動生成 hook + patterns.md リマインダ (D-15) を実行するスキル
</skills>
</context>

<tasks>

<task type="auto">
  <name>Task 1: ADR-0048 を書き (D-08 方針含む)、.planning/adr-categories.yaml と patterns.md に追記する</name>
  <files>docs/adr/0048-thread-files-folder-convention.md, .planning/adr-categories.yaml, .planning/patterns.md</files>
  <read_first>
    - docs/adr/0023-mcp-db-query-and-claude-code-tools.md (shared volume + env sanitization の先例 — 書き振り参考)
    - docs/adr/0026-thread-deletion-also-removes-threads-table-row.md (削除の原子性思想の先例)
    - docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md (YAML SSoT + 自動生成の先例)
    - .planning/adr-categories.yaml (カテゴリマッピング現状)
    - .planning/patterns.md `Data・Persistence` セクション末尾 (追記位置 + 書式)
    - .planning/phases/37-pdf-office-mcp/37-CONTEXT.md D-01..D-05 **および D-08** (規約 + 抽出失敗時挙動)
    - CLAUDE.md §"ADR Pattern Reference (GSD Integration)" (D-15 手動追記ルール)
  </read_first>
  <action>
  **(A) docs/adr/0048-thread-files-folder-convention.md を新規作成**

  構造テンプレート (既存 ADR 0023/0026 の section 構成に揃える、日本語):

  ```markdown
  # ADR-0048: thread-files 共有フォルダ規約 (Phase 37)

  **Status:** Accepted
  **Date:** 2026-04-XX (execute 時点の日付)
  **Phase:** 37 — ファイル入力 — PDF/Office 抽出 + MCP ツール参照
  **Supersedes:** なし
  **Related ADRs:** [0020](0020-fastmcp-docker-service-infrastructure.md), [0023](0023-mcp-db-query-and-claude-code-tools.md), [0026](0026-thread-deletion-also-removes-threads-table-row.md), [0044](0044-mcp-tool-catalog-single-source-of-truth.md)

  ## Context

  Phase 37 で PDF/Office ファイルの添付機能を実装するにあたり、以下を満たすフォルダ規約が必要になった:

  - ユーザー分離 (200 名規模・マルチユーザー運用)
  - thread 単位のライフサイクル (thread 削除で添付も消える、TTL/cron 不要)
  - api / mcp-server / worker の 3 サービス間で共有アクセス (worker は RO)
  - Phase 36 (アップロード UI) と Phase 38 (出力ストレージ) が同じ規約で接続できる

  ## Decision

  ### パス階層

  `/shared/thread-files/<github_login>/<thread_id>/` の 2 階層とする。

  - `github_login` は JWT payload から取得 (API 既存パターン、Phase 11-04 以降で確立)
  - `thread_id` は既存 LangGraph スレッド ID と同一値
  - `THREAD_FILES_DIR` 環境変数で base path を上書き可能 (テスト時の tmpdir 差し替え)

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

  - 先例: ADR-0023 `claude-code-outputs` shared volume
  - 先例: ADR-0026 thread 削除の原子性
  - 先例: ADR-0044 MCP カタログ SSoT (新規ツールの登録フロー)
  ```

  **(B) .planning/adr-categories.yaml に 0048 を追加**

  既存ファイルを読んで構造を確認した上で `Data・Persistence` カテゴリに追加:
  ```yaml
  # 例 (既存の書式に合わせる):
  Data・Persistence:
    - 0010
    - 0026
    - 0032
    - 0045
    - 0048   # Phase 37 thread-files フォルダ規約
  ```

  **(C) .planning/patterns.md の Data・Persistence セクションに 1 エントリ追加**

  既存セクション末尾 (Stdout 1 行 JSONL の後) に:
  ```markdown
  ### thread-files 共有フォルダ規約
  Phase 37 で導入。`/shared/thread-files/<github_login>/<thread_id>/` の 2 階層 named volume で
  api:RW / mcp-server:RW / worker:RO。thread 削除 (`adelete_thread` 直後の realpath guard + `shutil.rmtree`) と同期。
  ファイル命名は `YYYYMMDDTHHMMSS_<original>.<ext>`。`THREAD_FILES_DIR` 環境変数で base path を差し替え可能。
  抽出失敗 0 文字 PDF は `error` ではなく `content: ""` を返す (D-08)。
  Phase 36 (アップロード UI) / Phase 38 (出力ストレージ) が同じ規約で接続する。
  関連 ADR: [0048](../docs/adr/0048-thread-files-folder-convention.md)
  ```
  </action>
  <verify>
    <automated>test -s docs/adr/0048-thread-files-folder-convention.md && grep -q "^# ADR-0048" docs/adr/0048-thread-files-folder-convention.md && grep -q "^## Decision" docs/adr/0048-thread-files-folder-convention.md && grep -q "/shared/thread-files" docs/adr/0048-thread-files-folder-convention.md && grep -qE "content:\s*\"\"|content: \"\"" docs/adr/0048-thread-files-folder-convention.md && grep -q "0048" .planning/adr-categories.yaml && grep -q "thread-files 共有フォルダ規約" .planning/patterns.md</automated>
  </verify>
  <acceptance_criteria>
    - `docs/adr/0048-thread-files-folder-convention.md` が存在、60 行以上
    - `grep "^# ADR-0048" docs/adr/0048-thread-files-folder-convention.md` でマッチ
    - `grep -E "^## (Context|Decision|Consequences)" docs/adr/0048-thread-files-folder-convention.md` で 3 セクション以上マッチ
    - `grep "/shared/thread-files/<github_login>/<thread_id>/" docs/adr/0048-thread-files-folder-convention.md` でマッチ (パス規約明記)
    - `grep "YYYYMMDDTHHMMSS" docs/adr/0048-thread-files-folder-convention.md` でマッチ (命名規則明記)
    - `grep -E "api.*RW|mcp-server.*RW|worker.*RO" docs/adr/0048-thread-files-folder-convention.md` で 3 件マッチ (mount マトリクス)
    - `grep "Phase 36\|Phase 38" docs/adr/0048-thread-files-folder-convention.md` で両 phase への接続が記述されている
    - **S-02 対応:** `grep -E 'content:\s*\"\"|content: \"\"|content: ""' docs/adr/0048-thread-files-folder-convention.md` で 1 件以上マッチ、かつ `grep -E "D-08|テキスト.*0 文字|抽出失敗" docs/adr/0048-thread-files-folder-convention.md` で 1 件以上マッチ
    - `grep "0048" .planning/adr-categories.yaml` でマッチ
    - `grep "thread-files 共有フォルダ規約" .planning/patterns.md` でマッチ
    - `grep "Data・Persistence" .planning/patterns.md` の後に thread-files エントリが位置する (セクション配置)
  </acceptance_criteria>
  <done>ADR-0048 が書かれ (D-08 方針を含む)、patterns.md と adr-categories.yaml も整合する</done>
</task>

<task type="auto">
  <name>Task 2: pre-commit hook で INDEX.md を再生成し、整合を確認する</name>
  <files>docs/adr/INDEX.md</files>
  <read_first>
    - docs/adr/INDEX.md (現在の状態)
    - scripts/generate_adr_index.py (自動生成ロジック)
    - scripts/install-hooks.sh (hook インストール状況)
    - .planning/adr-categories.yaml (Task 1 で更新済み)
  </read_first>
  <action>
  **(A) hook 経由での生成**

  ADR INDEX は pre-commit hook (`scripts/install-hooks.sh` でインストール) が自動再生成する。手動で触らない。
  この段階で `docs/adr/0048-*.md` を `git add` し、以下を実行して hook を発火させる:

  ```bash
  git add docs/adr/0048-thread-files-folder-convention.md .planning/adr-categories.yaml
  git commit -m "docs(adr): add ADR-0048 thread-files folder convention (Phase 37)" --only docs/adr/0048-thread-files-folder-convention.md .planning/adr-categories.yaml
  # hook が INDEX.md を再生成して自動 stage/commit に含めるはず
  ```

  hook 未インストールなら手動生成:
  ```bash
  python3 scripts/generate_adr_index.py
  git add docs/adr/INDEX.md
  ```

  **(B) 生成結果の確認**

  ```bash
  grep "0048" docs/adr/INDEX.md
  # → | [0048](0048-thread-files-folder-convention.md) | ADR-0048: thread-files 共有フォルダ規約 (Phase 37) | YYYY-MM-DD |
  ```

  **Total:** 行の件数が 1 件増えている (44 → 45 件):
  ```bash
  grep "^\*\*Total:\*\*" docs/adr/INDEX.md
  # 旧: **Total:** 44 件(欠番 3 件: 0015, 0016, 0017)
  # 新: **Total:** 45 件(欠番 3 件: 0015, 0016, 0017)
  ```

  **(C) patterns.md は手動更新 (D-15)**

  Task 1 (C) で既に追記済みのはず。再度確認:
  ```bash
  grep -A 3 "### thread-files 共有フォルダ規約" .planning/patterns.md
  ```
  </action>
  <verify>
    <automated>grep -q "0048" docs/adr/INDEX.md && grep -q "thread-files" docs/adr/INDEX.md && grep -qE "\*\*Total:\*\* (45|46|47)" docs/adr/INDEX.md</automated>
  </verify>
  <acceptance_criteria>
    - `docs/adr/INDEX.md` の `Data・Persistence` セクション配下に ADR 0048 のエントリが 1 行ある
    - `grep "^\*\*Total:\*\*" docs/adr/INDEX.md` で 45 件以上 (44 → 45 以上に増加)
    - INDEX.md のエントリと ADR ファイル名が一致する (`0048-thread-files-folder-convention.md`)
    - INDEX.md の Data テーブルで新エントリの Date カラムが埋まっている
  </acceptance_criteria>
  <done>INDEX.md が自動生成され、エントリが反映される</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Integration check — docker compose 実環境で end-to-end 1 経路動作確認</name>
  <what-built>
    - 新規 MCP ツール `attachments_list` / `attachments_extract`
    - docker-compose `thread-files` volume + 3 サービス mount
    - LangGraphHandler の SystemMessage prepend
    - delete_thread hook によるフォルダ削除 (realpath guard 付き)
  </what-built>
  <how-to-verify>
  **準備**
  1. Phase 37 ブランチを checkout して `docker compose up -d --build mcp-server api worker frontend postgres redis` を実行
  2. `docker compose logs -f mcp-server` と `docker compose logs -f worker` を別ターミナルで tail
  3. ブラウザで `http://localhost:5173/orochi/` にアクセスして Device Flow ログイン

  **Scenario A: 添付ファイル scan + SystemMessage hint**
  1. 任意の Chat スレッドを新規作成 (thread_id を控える)
  2. 以下でサンプル PDF を thread フォルダに配置:
     ```bash
     # サンプル PDF を手元で用意しておく (任意の軽量 PDF)
     docker compose exec api mkdir -p /shared/thread-files/<github_login>/<thread_id>
     docker compose cp samples/sample.pdf api:/shared/thread-files/<github_login>/<thread_id>/20260421T120000_sample.pdf
     ```
  3. 同じ thread で Chat にメッセージを送る (例: 「何か添付されていますか?」)
  4. AI の応答に「sample.pdf が添付されている」旨の言及があること (scan + hint が効いた証拠)
  5. `docker compose logs worker | grep "添付ファイル"` で SystemMessage 注入の痕跡を確認 (optional — デバッグログがあれば)

  **Scenario B: attachments_extract 呼び出し**
  1. 同じ thread で「sample.pdf の内容を教えて」とメッセージ
  2. AI が `attachments_extract` ツールを呼び、内容を要約して返すこと
  3. `docker compose logs mcp-server | grep attachments_extract` でツール呼び出しログを確認

  **Scenario C: path traversal 拒否**
  1. Canvas アプリ (Phase 19 以降のアプリ) から iframe-rpc 経由で `extract_attachment('../../../etc/passwd')` を試す
     (もしくは API テストで直接 mcp-server の `/internal/call_tool` に POST)
  2. `error.code == "corrupt"` または `"invalid filename"` メッセージが返ること

  **Scenario D: thread 削除で folder が消える**
  1. Chat UI で Scenario A の thread を削除
  2. `docker compose exec api ls /shared/thread-files/<github_login>/` で該当 thread フォルダが消えていること
  3. フォルダ不在でも API が 204 を返す

  **Scenario E: 0 文字 PDF の扱い (D-08 検証)**
  1. サンプルとしてスキャン PDF (テキスト抽出できない PDF) を thread フォルダに配置
  2. `attachments_extract` を呼び、レスポンスが `{"content": "", "error": null, ...}` であること
     (error ではなく空文字列 content が返る)
  3. AI がユーザーに "テキスト抽出できませんでした" 旨を説明できること

  **観察結果の記録**
  `docs/phase-37-integration-check.md` に以下のテンプレートで結果を記録する:

  ```markdown
  # Phase 37 Integration Check

  **Date:** YYYY-MM-DD
  **Executor:** (name)
  **Branch:** gsd/phase-37-pdf-office-mcp

  ## 観察結果

  ### Scenario A: 添付 scan + SystemMessage
  - [ ] AI が添付ファイルを認識して応答した (sample.pdf に言及)
  - log / screenshot: ...

  ### Scenario B: attachments_extract
  - [ ] AI が ツール呼び出しで PDF を要約した
  - mcp-server log 抜粋: ...

  ### Scenario C: Path traversal 拒否
  - [ ] `error.code == "corrupt"` が返った

  ### Scenario D: delete_thread で folder 削除
  - [ ] folder が消えた。API は 204 を返した

  ### Scenario E: 0 文字 PDF (D-08)
  - [ ] content: "" が返り、error は null
  - [ ] AI が "テキスト抽出できませんでした" と説明した

  ## Silent failure 検知
  - unit test 全 passed だが実環境で発覚した不整合があれば記録
  - (なければ "検知なし" と記入)

  ## 起動時間
  - mcp-server healthcheck first-ready: ___ 秒 (start_period=60s で間に合ったか)
  - magika/onnxruntime 初回 import ログ抜粋: ...
  ```
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues (例: "Scenario B failed: AI は attachments_extract を呼ばず推測応答した")</resume-signal>
</task>

<task type="auto">
  <name>Task 4: VALIDATION.md の Wave 3 行追記 + frontmatter を `nyquist_compliant: true` / `status: validated` に最終化する</name>
  <files>.planning/phases/37-pdf-office-mcp/37-VALIDATION.md</files>
  <read_first>
    - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md (Plan 02/03/04 で段階的に埋まった状態)
    - Validation Sign-Off セクションの現行状態
  </read_first>
  <action>
  **B-07 対応:** Per-Task Map は既に Plan 02/03/04 の Task で Wave 0/1/2 分が追記されている前提。
  本 Task では **Wave 3 (Plan 05) 分を追加** + **frontmatter 最終化** + **Sign-Off チェック完了** を行う。

  **(A) Per-Task Verification Map テーブル末尾に Wave 3 行を追記**

  ```markdown
  | 37-05-01 | 05 | 3 | FIN-03,FIN-04 | — | ADR-0048 + patterns.md 追記 | smoke | `grep "0048" docs/adr/INDEX.md && grep "thread-files" .planning/patterns.md` | ✅ | ⬜ pending |
  | 37-05-02 | 05 | 3 | FIN-03,FIN-04 | — | ADR-0048 D-08 方針記載 (S-02) | smoke | `grep -E "content:\s*\"\"\|テキスト.*0 文字" docs/adr/0048-thread-files-folder-convention.md` | ✅ | ⬜ pending |
  | 37-05-03 | 05 | 3 | FIN-03,FIN-04 | T-37-05-01 | integration check 記録 | human | `test -s docs/phase-37-integration-check.md` | ✅ | ⬜ pending |
  | 37-05-04 | 05 | 3 | — | — | VALIDATION.md 最終化 | smoke | `grep -q "nyquist_compliant: true" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md` | ✅ | ⬜ pending |
  ```

  **(B) frontmatter を最終化**

  現行 (Plan 02 Task 4 後):
  ```yaml
  ---
  phase: 37
  slug: pdf-office-mcp
  status: draft
  nyquist_compliant: false
  wave_0_complete: true
  created: 2026-04-21
  ---
  ```

  最終化 (Plan 05 Task 4 完了時):
  ```yaml
  ---
  phase: 37
  slug: pdf-office-mcp
  status: validated          # draft → validated
  nyquist_compliant: true    # false → true
  wave_0_complete: true
  created: 2026-04-21
  validated: 2026-04-XX      # 本 Task 実行日
  ---
  ```

  **(C) Validation Sign-Off セクションのチェックボックスを ON に**

  現行:
  ```markdown
  - [ ] All tasks have `<automated>` verify or Wave 0 dependencies
  - [ ] Sampling continuity: no 3 consecutive tasks without automated verify
  - [ ] Wave 0 covers all MISSING references (extract/list テストスタブ + delete hook テスト)
  - [ ] No watch-mode flags
  - [ ] Feedback latency < 30s
  - [ ] `nyquist_compliant: true` set in frontmatter

  **Approval:** pending
  ```

  更新後:
  ```markdown
  - [x] All tasks have `<automated>` verify or Wave 0 dependencies
  - [x] Sampling continuity: no 3 consecutive tasks without automated verify
  - [x] Wave 0 covers all MISSING references (extract/list テストスタブ + delete hook テスト)
  - [x] No watch-mode flags
  - [x] Feedback latency < 30s
  - [x] `nyquist_compliant: true` set in frontmatter

  **Approval:** approved (Phase 37 Plan 05 Task 4 にて更新)
  ```

  **(D) 段階更新コメントも最新状態に更新**

  Plan 02 Task 4 で追加した "Staged update" ブロックを、Wave 3 完了後は以下に置き換える:
  ```markdown
  > **Staged update completed:**
  > - [x] Wave 0: Plan 02 Task 4 で埋めた (37-01-XX / 37-02-XX)
  > - [x] Wave 1: Plan 03 Task 4 で埋めた (37-03-XX)
  > - [x] Wave 2: Plan 04 Task 3 で埋めた (37-04-XX)
  > - [x] Wave 3: Plan 05 Task 4 で埋めた (37-05-XX) + frontmatter 最終化
  ```
  </action>
  <verify>
    <automated>grep -q "nyquist_compliant: true" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md && grep -q "wave_0_complete: true" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md && grep -q "status: validated" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md && grep -c "^| 37-05-" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md | awk '{if ($1 >= 3) exit 0; else exit 1}'</automated>
  </verify>
  <acceptance_criteria>
    - VALIDATION.md frontmatter が `nyquist_compliant: true`
    - VALIDATION.md frontmatter が `wave_0_complete: true`
    - VALIDATION.md frontmatter が `status: validated`
    - Per-Task Verification Map に `^| 37-05-` 行が 3 件以上
    - Per-Task Verification Map 全体で 15 行以上 (Wave 0+1+2+3 合計)
    - `Approval:` 行が `approved` になっている
    - Sign-Off チェックボックス 6 項目が全 `[x]`
    - 段階更新コメントが "Staged update completed" に更新されている
  </acceptance_criteria>
  <done>VALIDATION.md が Phase 37 の完了を追跡可能な形で完結する</done>
</task>

</tasks>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ADR (persistent documentation) → future phase planner | 規約の曖昧さが Phase 36/38 で不整合実装を生む |
| Integration check (manual) → CI / audit | human-in-the-loop 検査の抜け漏れ |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-37-05-01 | Repudiation | Integration check 結果が記録されず、後日「動作確認していない」証跡不明で phase close されてしまう | mitigate | ADR-0046 の `Integration check gate` を本 phase 内で強制適用。`docs/phase-37-integration-check.md` を artifact として必須 (Task 3 checkpoint blocking) |
| T-37-05-02 | Information Disclosure | Integration check 中に test 用 JWT / github_token ログ を含むスクリーンショットが ADR / docs に残る | mitigate | Task 3 の `docs/phase-37-integration-check.md` テンプレートで secrets を手動除去する責務を明記。reviewer が目視で確認 |

</threat_model>

<verification>
- `ls docs/adr/0048-*.md` で 1 ファイル
- `grep "0048" docs/adr/INDEX.md` でヒット
- `grep "thread-files" .planning/patterns.md` でヒット
- `ls docs/phase-37-integration-check.md` で存在
- `grep "nyquist_compliant: true" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md` でマッチ
- `grep "status: validated" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md` でマッチ
- VALIDATION.md Per-Task Map の行数が 15 以上 (全 Wave 分合計)
</verification>

<success_criteria>
- Success Criteria 5 (フォルダ規約の ADR 化 + Phase 36/38 接続) が文書として達成
- ADR-0048 に D-08 (0 文字 PDF 時の content:"" 返却) が明記されている (S-02 対応)
- Integration check 1 経路以上 (Scenario A-E) が実環境で動いたエビデンスが残る
- VALIDATION.md が nyquist_compliant: true になり phase が verify-ready (全 Wave の Per-Task Map が埋まっている)
</success_criteria>

<output>
After completion, create `.planning/phases/37-pdf-office-mcp/37-05-SUMMARY.md`.
</output>
