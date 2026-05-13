# Phase 38: ファイル出力 — worker 生成 DL + プレビュー + ユーザー別保持 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `38-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 38-worker-dl
**Areas discussed:** ストレージ規約, 出力永続化経路, プレビュー対象と表示方式, 過去スレッドからの再取得 UI

---

## ストレージ規約

### Q1. AI 生成ファイルの保存先とライフサイクル

| Option | Description | Selected |
|--------|-------------|----------|
| `_generated/` サブフォルダ | `/shared/thread-files/<login>/<tid>/_generated/<name>`、ADR-0048 拡張、thread 削除と同期で消える。input/output をサブフォルダで明示分離、attachments_list もフィルターで両方見える。realpath guard / JWT 認可をそのまま使える。 | ✓ |
| フラット混在 | input と output を区別せず同階層に置く。コード簡潔だが衝突リスクと kind フラグ管理が必要。 | |
| 独立 volume (thread-outputs) | 新規 volume、thread 削除後も残す。スレッドをまたいだ哲学になり、Phase 37 規約と二重管理。 | |

**User's choice:** `_generated/` サブフォルダ
**Notes:** Phase 37 ADR-0048 規約の最小拡張という方向性を採用。ライフサイクルも Phase 37 D-03 と完全一致。

### Q2. AI 生成ファイルを既存 attachments 経路でどこまで一体化するか

| Option | Description | Selected |
|--------|-------------|----------|
| API ルートは分離、MCP ツールは拡張 | HTTP: `GET /api/threads/{tid}/outputs/{name}` 新設、MCP: `attachments_list` に `kind` フィールド追加で `_generated/` も含めて返す。UI/API は明示的、ツールは最小追加。 | ✓ |
| 完全に分離 | HTTP 新設 + MCP 新規 `outputs_list` / `outputs_read` ツール追加。AgentState も outputs フィールド分離。コード重複多く、Phase 30 SSoT のツール数も増える。 | |
| 完全に一体化 | `_generated/` の区別を API/MCP でもさせず、attachments_list が全部返し、GET /attachments/{name} も含めて取れる。UX 辻褄不一致。 | |

**User's choice:** API ルートは分離、MCP ツールは拡張
**Notes:** UI/API レイヤーでは明示分離、MCP レイヤーでは `kind` discriminator で 1 ツールにまとめる、というハイブリッドが選ばれた。

### Q3. AI が同名ファイルを 2 回生成した場合

| Option | Description | Selected |
|--------|-------------|----------|
| 後勝ち (上書き) | basename そのまま、最新で上書き。AI の "前回のを修正して" メンタルモデルに自然。 | |
| timestamp prefix (Phase 37 D-02 踏襲) | `YYYYMMDDTHHMMSS_<name>` で必ず unique。履歴を残す。AI には flat list で見せて参照可。 | ✓ |
| 連番 suffix (output_1.png) | basename 読みやすい、update 意図が新ファイルになるケース有り。 | |

**User's choice:** timestamp prefix (Phase 37 D-02 踏襲)
**Notes:** 履歴監査と Phase 37 規約統一を優先。AI の update メンタルモデルとは多少ずれるが意図的なトレードオフ。

### Q4. AI 生成ファイルのユーザー手動削除

| Option | Description | Selected |
|--------|-------------|----------|
| 個別削除可能 | `DELETE /api/threads/{tid}/outputs/{name}` 新設、UI からゴミ箱ボタン。 | |
| thread 削除のみ (Phase 37 D-03 踏襲) | 個別削除ルートを作らず、thread 削除でのみ消える。surface 最小。 | ✓ |
| AI 経由で削除 | MCP `outputs_delete` で AI に依頼。UI ボタンなし、対話型 UX。 | |

**User's choice:** thread 削除のみ (Phase 37 D-03 踏襲)
**Notes:** Phase 37 D-03 と完全一致。個別削除 UX は v6.1+ に deferred。

---

## 出力永続化経路

### Q1. execute_python / claude_code の生成ファイルを _generated/ に運ぶ主要経路

| Option | Description | Selected |
|--------|-------------|----------|
| sandbox 内で直接書き込む | cwd を _generated/ に切り替え、subprocess がそこへ直接書く。subprocess 終了後も消えない。 | ✓ |
| 完了後 worker が scan & コピー | cwd は /tmp のまま、handler が完了後に scan して _generated/ にコピー。worker は RO のため設計追加要。 | |
| AI が明示的に save_output MCP tool を呼ぶ | 新規ツール導入、AI プロンプトで「保存して」と言わないと永続化されないリスク。 | |

**User's choice:** sandbox 内で直接書き込む (cwd 切り替え方式)
**Notes:** mcp-server は thread-files に RW mount 済 (Phase 37 D-04) なので cwd 切り替えだけで動く前提。

### Q2. execute_python sandbox に _generated/ をどう伝えるか

| Option | Description | Selected |
|--------|-------------|----------|
| cwd を _generated/ に切り替え | `open("foo.png","w")` で自然に書ける。x-thread-id / x-github-login ヘッダから path 構築。 | ✓ |
| OUTPUT_DIR env var で示し cwd=/tmp のまま | 中間ファイル隔離が綺麗。ただし AI に env var の使い方を教える追加 prompt が要る。 | |

**User's choice:** cwd を _generated/ に切り替え
**Notes:** AI の Python コード書き味を素直に保つ判断。中間ファイル隔離はトレードオフとして受容。

### Q3. timestamp prefix は誰がどこで付けるか

| Option | Description | Selected |
|--------|-------------|----------|
| MCP tool が実行後に検出し rename | AI は basename で書ける、tool wrapper が rename で `{ts}_{name}` に統一。AI プロンプト依存ゼロ。 | ✓ |
| exec ごとの unique subdir | cwd を `_generated/{ts}_{exec_id}/` にし basename のまま書く。UI 側 grouping renderer 要。 | |
| AI が sandbox 内で prefix を付ける | TIMESTAMP env var を渡し AI が `f"{ts}_..."` で書く。AI プロンプト依存、抜け漏れリスク。 | |

**User's choice:** MCP tool が実行後に検出し rename
**Notes:** 規約遵守を AI プロンプトに依存させない方針。検出ロジック (snapshot diff vs mtime) は planner 判断。

### Q4. claude_code の cwd

| Option | Description | Selected |
|--------|-------------|----------|
| default cwd を _generated/ にし override 不可 | cwd 引数を削除、常に _generated/ で動く。overflow output は Phase 23 ADR-0023 維持で global volume のまま。 | ✓ |
| default cwd を _generated/, 引数で override 可 | 柔軟だが他 thread への漏出リスクあり。 | |
| 現状維持 (cwd=/tmp), 完了後コピー | execute_python と経路がずれる、/tmp 内のゴミも取りかねない。 | |

**User's choice:** default cwd を _generated/ にし override 不可
**Notes:** UX 統一・規約遵守保証。Phase 23 overflow output (claude-code-outputs volume) は debug 用として残す。

### Q5. GET /api/threads/{tid}/outputs/{name} の {name}

| Option | Description | Selected |
|--------|-------------|----------|
| timestamp prefix 付きの実体 name | URL: `/outputs/20260511T120000_output.png`、API シンプル、UI 一覧もそのまま使える。 | ✓ |
| basename + サーバ側で最新解決 | URL: `/outputs/output.png` だけ、サーバ scan で最新解決。古い版はクエリパラメータ。 | |
| 両方サポート | basename = 最新 / full = 該当版。認可と realpath guard 二重化。 | |

**User's choice:** timestamp prefix 付きの実体 name
**Notes:** AI / UI / API で同一 identity 文字列を扱う。最新解決ロジックの曖昧さを避ける。

---

## プレビュー対象と表示方式

### Q1. v6.0 Phase 38 でプレビュー対応するフォーマットの範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 画像 + Markdown + CSV + テキスト系 | 画像 (png/jpg/gif/webp), Markdown, CSV (テーブル描画), プレーンテキスト系 (Monaco syntax highlight)。PDF は DL のみ。HTML は除外。 | ✓ |
| 画像 + Markdown のみ (ミニマル) | FOUT-03 明記例だけ、CSV / テキストは DL のみ。 | |
| 画像 + Markdown + CSV + テキスト + PDF (フルセット) | pdf.js / iframe で PDF も。bundle 増、CSP 設計増。 | |

**User's choice:** 画像 + Markdown + CSV + テキスト系
**Notes:** PDF は DL のみ・v6.1+ 検討。HTML は Canvas との衝突回避で除外。

### Q2. AI 生成ファイルのプレビュー表示方式

| Option | Description | Selected |
|--------|-------------|----------|
| 画像は inline、他はチップ+展開 | 画像のみ AI 応答内に inline、Markdown/CSV/テキストはチップ → 展開。 | |
| 全部 inline にレンダリング | チャットバブル内に画像・テーブル・コードブロック混在。スクロール厳しいケース有り。 | |
| 全部チップ一覧、クリックでモーダル (Phase 36 と統一) | チップだけ並べ、クリックでモーダル。Phase 36 アップロード UX と完全一致。 | ✓ |
| スレッド右にサイドペイン | Canvas 風 split pane、複数ファイル比較可。layout 説明重い。 | |

**User's choice:** 全部チップ一覧、クリックでモーダル (Phase 36 と統一)
**Notes:** Phase 36 アップロード添付の UX と統一する判断。AttachmentChip / AttachmentModal を `kind` 対応に拡張して再利用。

### Q3. 1 turn 内で複数 tool 呼び出しがあった場合のチップ集約

| Option | Description | Selected |
|--------|-------------|----------|
| AI 最終 message にすべて bundle | turn 完了時にまとめて反映、中間呼び出しはチップ描画しない。Phase 36 と同メンタルモデル。 | ✓ |
| tool 呼び出しごとにチップ | 中間呼び出しごとに streaming で出す。tool call UI 設計追加要。 | |
| 別「Generated」セクション | 各 AI turn 下に固定セクション、視覚ノイズ増。 | |

**User's choice:** AI 最終 message にすべて bundle
**Notes:** Phase 36 attachments と同じ「message に bundle」モデルでメンタルモデル統一。

### Q4. アップロード添付 (Phase 36) と AI 生成 (Phase 38) のチップ区別

| Option | Description | Selected |
|--------|-------------|----------|
| ラベル付き | チップに「AI 生成」「添付」ラベル + わずかな色味調整。AttachmentChip に kind props 追加で再利用。 | ✓ |
| 同デザイン、区別なし | 視覚的にシンプル、kind フィールドは API 内部のみ。誤認識リスク。 | |
| 色 + アイコンで強めに区別 | 視覚的一目瞭然、Phase 36 デザインシステムとずれる可能性。 | |

**User's choice:** ラベル付き
**Notes:** 軽い区別で input / output の境界を示しつつ Phase 36 UX を踏襲。UI 詳細は `/gsd-ui-phase` で確定。

---

## 過去スレッドからの再取得 UI

### Q1. FOUT-04「一覧画面から再取得」のスコープ

| Option | Description | Selected |
|--------|-------------|----------|
| スレッドを開いて見る | ThreadSidebar から過去スレッドを開き、message bundle のチップから再取得。横断 UI 追加なし。 | ✓ |
| 横断 My Files 画面追加 | サイドバー / メニューに My Files、user_id 単位で全スレッド集約。endpoint 追加 + UI 設計。 | |
| Header / Sidebar に file dropdown | ヘッダから最近生成ファイル dropdown。件数上限 UX 設計要。 | |

**User's choice:** スレッドを開いて見る
**Notes:** Phase 38 scope を minimum surface に保つ判断。横断 UI は v6.1+ で要件次第。

### Q2. スレッドを開いたときの生成ファイル一覧表示

| Option | Description | Selected |
|--------|-------------|----------|
| AI message に bundle されたチップだけ、一覧なし | LangGraph checkpoint の message metadata からそのまま復元。追加 UI / endpoint なし。 | ✓ |
| message チップ + スレッド上部に「Files」tab/パネル | チップ + 1 スレッド scope の一覧 tab。GET /threads/{tid}/outputs 追加要。 | |
| message チップ + ThreadSidebar 拡張 | sidebar 各スレッドエントリ展開で file tree。複雑、UI 設計負荷大。 | |

**User's choice:** AI message に bundle されたチップだけ、一覧なし
**Notes:** Phase 36 attachments と同パターン。一覧 endpoint も新設しない。

### Q3. SystemMessage prepend (Phase 37 D-11) に _generated/ を含める際の context 肥大化対策

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 37 D-11 そのまま (制限なし) | name + size + timestamp + kind の薄いメタデータを両方含む flat list。v6.0 規模 (5000 chars 程度) で十分。 | ✓ |
| input/output を別セクション、output は直近 10 件のみ | 長期スレッドで context 食い潰し対策、AI には件数表記で残り示す。 | |
| 件数だけ表記、詳細は attachments_list で | 最軽量、AI が毎回 tool 呼ぶ latency 増。 | |

**User's choice:** Phase 37 D-11 そのまま (制限なし)
**Notes:** v6.0 規模では十分という判断。件数爆発時に v6.1+ で見直し。

### Q4. FOUT-04 success criteria 5 (multi-user isolation) の検証方針

| Option | Description | Selected |
|--------|-------------|----------|
| 自動テスト必須 | outputs route 向けに pytest 追加 (別 user JWT で 404 / path traversal 拒否)。 | |
| Phase 36 テストを再利用 (追加テストなし) | outputs route が `_resolve_thread_folder` / `_safe_resolve_file` を経由するのでスモークテストのみ。 | ✓ |
| 手動 manual check + curl 検証 | VERIFICATION.md に手順記述のみ。リグレッション検出なし。 | |

**User's choice:** Phase 36 テストを再利用 (追加テストなし)
**Notes:** Phase 36 で実装された realpath guard / JWT 認可テストが outputs route にも効くという前提。outputs route の helper 経由を保証するスモークテストで担保。

---

## Claude's Discretion

- `AgentState.attachments` の拡張方針 (input/output 統合 vs `outputs` 独立フィールド) — D-06 / D-13 の `kind` discriminator 統一方針に揃え、`attachments` 拡張 (kind フィールド) に倒すのが筋。planner 確認。
- D-10 timestamp prefix rename の検出ロジック (snapshot diff vs mtime 判定) — planner 判断 (D-11)。
- AI 最終 message metadata bundle の永続化方式 (LangGraph checkpoint の標準 message metadata 機構を使うか、別 field か) — planner 確認。
- `_generated/` ディレクトリのオンデマンド作成タイミング (handler scan 時 mkdir -p)。
- AttachmentChip の `kind` ラベル文言・色・アイコン — `/gsd-ui-phase` で UI-SPEC として確定。
- AI に見せる `attachments_list` 戻り値の sort / grouping (timestamp 降順 / kind 別など) — Phase 37 D-11 踏襲。
- MarkdownMessage.tsx は D-13 により inline 描画しない方針なので追加変更不要。AI プロンプトで `_generated/` path 言及を抑制するチューニング余地は planner で。
- 中間ファイル / orphan ファイルの GC (D-08) — 観察ベースで v6.1+。

## Deferred Ideas

- 個別削除 UI (DELETE /api/threads/{tid}/outputs/{name}) — v6.1+
- 横断 "My Files" 画面 / Header dropdown — v6.1+
- timestamp prefix で溜まる古いファイルの自動 GC — v6.1+
- `AgentState.outputs` 独立フィールド化 — Claude 裁量で attachments 拡張に倒す
- PDF プレビュー (pdf.js / iframe) — v6.1+
- HTML プレビュー — Canvas と用途衝突、Phase 16 系で扱う
- AI の "ファイルを更新する" メンタルモデル — timestamp prefix で historical immutable、prompt hint 調整余地
- CSV / Table 行数上限 (1000 行超え時の summary) — UI 観察次第
- 画像サムネ生成 — Phase 36 D-23 と同じくやらない方針踏襲
- AI 生成完了の toast / 通知 — v6.1+ UI polish
- `session-state/files/` paths の AI 応答テキスト残留時の自動マッピング — D-13 で inline 描画しないため不要
- MCP `outputs_list` / `outputs_read` 単独ツール化 — `attachments_list` 拡張で兼用

---

*Phase: 38-worker-dl*
*Discussion conducted: 2026-05-11*
