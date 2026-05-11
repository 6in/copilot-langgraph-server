# Phase 36: ファイル入力 — text/code + image multimodal - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 36-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 36-text-code-image-multimodal
**Areas discussed:** 受付ポリシー、画像 multimodal の配線方式、添付 UX とアップロードタイミング、multimodal 非対応モデルの fallback、履歴上の添付可視化とチェックポイント保存

---

## Gray area selection

| Option | Description | Selected |
|--------|-------------|----------|
| 画像 multimodal の配線方式 | Copilot SDK 0.2.0 への添付渡し（base64 inline / path / SystemMessage embed）の最大リスク領域 | ✓ |
| 添付 UX とアップロードタイミング | 即時 vs 送信時、drop/paste、キャンセル時のファイル扱い | ✓ |
| multimodal 非対応モデルの fallback | 警告バナー / 📎 disable / worker 側 drop の graceful 設計 | ✓ |
| 履歴上の添付可視化とチェックポイント保存 | HumanMessage.additional_kwargs / thread folder / API エンドポイント設計 | ✓ |

**User's choice:** 全 4 area を議論。さらに「受付ポリシー（拡張子・サイズ・件数）」を sub-area として追加選択。

---

## 受付ポリシー（拡張子・サイズ・件数）

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 37 踏襲 + 画像枠のみ追加 | text/code は 100MB/50k文字/200k文字を Phase 37 から引き継ぎ、画像は 10MB/5枚/.png,.jpg,.webp を新規定義 | ✓ |
| Phase 36 で新規ポリシー議論 | 上限等を独立して検討 | |
| policy 自体を defer して最小限のガードのみ | 100MB + 5 件だけ守り、細かい policy は Phase 39 polish へ | |

**User's choice:** Phase 37 踏襲 + 画像枠のみ追加 → D-01 / D-02

---

## Area 1: 画像 multimodal の配線方式

### Q1-A: Copilot SDK への添付 API 採用範囲（初回）

| Option | Description | Selected |
|--------|-------------|----------|
| send_and_wait(attachments=[...]) を採用 | SDK native API を ChatCopilot._agenerate / _astream で呼ぶ。FileAttachment + BlobAttachment 両対応 | ディスカッション要求 |
| prompt embed のみ | ファイル名・サイズ・抜粋だけ prompt 文字列に埋め込む。画像扱えず FIN-02 不可 | |
| LangChain multimodal content-parts 変換層 | HumanMessage(content=[{type:image_url,...}]) を受けて BlobAttachment 変換 | |

**User's choice:** ディスカッションして決める → 下の Q1-B で envelope に言語化して再質問

### Q1-B: ラッパーの attachments 受け取り envelope（再質問）

| Option | Description | Selected |
|--------|-------------|----------|
| (a) HumanMessage.additional_kwargs[attachments] サイドカー | dict list を additional_kwargs に積み、ラッパーが copilot.* 型に変換 | ✓ |
| (b) LangChain multimodal content-parts + additional_kwargs 併用 | 画像だけ content-parts、text は kwargs。分岐増えてバグ入りやすい | |
| (c) ainvoke(..., attachments=[copilot.*]) kwarg スルー | handler が SDK 型を直接組み立て。SDK 型漏れで Technical Preview 影響拡大 | |

**User's choice:** (a) HumanMessage.additional_kwargs[attachments] → D-10

### Q2: 画像は FileAttachment / BlobAttachment どっち

| Option | Description | Selected |
|--------|-------------|----------|
| FileAttachment (path) のみ | 画像も text/code も /shared/thread-files 下の path を SDK に渡す。base64 コピーオーバーヘッド回避 | ✓ |
| BlobAttachment (base64) のみ | api で base64 + MIME を付けて渡す。SDK subprocess のファイルアクセス非依存 | |
| ハイブリッド（text=path / 画像=blob） | 画像は MIME 明示の base64、text は path | |

**User's choice:** FileAttachment (path) のみ → D-09

### Q3: text/code の LLM 渡し方

| Option | Description | Selected |
|--------|-------------|----------|
| attachments で毎 turn eager に渡す | text/code も FileAttachment で渡し、LLM が最初から内容を見える。attachments_extract は execute_python sandbox と PDF/Office 用途に責任集中 | ✓ |
| Phase 37 方式踏襲（tool 経由 lazy fetch） | SystemMessage メタ情報のみ。LLM が読みたい時 attachments_extract | |
| ハイブリッド（小さいファイル eager / 大きいファイル lazy） | 5000 文字閾値で分岐 | |

**User's choice:** attachments で毎 turn eager → D-11

### Q4: 添付をいつ渡すか

| Option | Description | Selected |
|--------|-------------|----------|
| 新規添付のみ | user turn で新たに添付されたファイルのみ attach。過去添付は SystemMessage メタ + LLM 文脈記憶 | ✓ |
| thread folder 全件を毎 turn attach | 過去添付も毎回含める。token 肥大 + 重複読み込み | |
| LLM が任意ファイルを使える lazy attach | 全件メタ提示 + tool 経由取得（画像不可で Phase 37 完全踏襲） | |

**User's choice:** 新規添付のみ → D-11

### Q5: Attachment dict 標準スキーマ

| Option | Description | Selected |
|--------|-------------|----------|
| リクエスト / state / DB / MCP tool 戦用の単一スキーマ | Phase 37 の attachments_list 戻り値 {name, size, modified_at, ext} を拡張し全層で統一 | ✓ |
| 層ごとに別スキーマ | API / job payload / AgentState / SDK 専用で変換レイヤー | |
| planner 判断に defer | 具体スキーマは planner で決定 | |

**User's choice:** 単一スキーマ → D-14 / D-15

---

## Area 2: 添付 UX とアップロードタイミング

### Q1: Upload timing

| Option | Description | Selected |
|--------|-------------|----------|
| 即時 upload → チップ表示時点でサーバー保持 | ChatGPT / Claude 方式。POST /api/threads/{id}/attachments で即 /shared/thread-files/ へ | ✓ |
| 送信時一括 upload (multipart with chat) | POST /api/chat multipart で upload + LLM 呼び出し一体 | |
| 二段: draft upload + finalize on send | pending フォルダ → 送信成功時に rename。フォルダ規約と不整合 | |

**User's choice:** 即時 upload → D-03

### Q2: 添付の入り口（multiSelect）

| Option | Description | Selected |
|--------|-------------|----------|
| 📎 ボタンからファイルピッカー | InputBar toolbarSlot に Phase 35 予約済みのボタン | ✓ |
| Drag & Drop（InputBar 内 / 全画面） | textarea or チャット領域への drop。over 時 border 強調 | ✓ |
| Ctrl+V / クリップボード画像ペースト | textarea focus 中の paste から image/* blob | ✓ |
| フォルダ / URL / 外部ファイルストレージ連携 | GitHub / Drive / URL import。scope 超え | ✓ (reconsidered) |

**User's initial choice:** 全 4 つ選択。scope creep 指摘のためフォロー質問（下記）で外部ストレージを defer 決定。

### Q2-Follow: 外部ストレージ連携

| Option | Description | Selected |
|--------|-------------|----------|
| 未来の phase へ defer | Phase 36 はローカル File API のみ | ✓ |
| URL import だけ Phase 36 に入れる | SSRF / 認証サイトの扱いで scope 肥大リスク | |
| 全て Phase 36 に入れる（scope 拡張） | OAuth スコープ拡張 + API Rate Limit + OAuth UI 必要 | |

**User's choice:** defer → deferred section / D-04 の入り口は 📎 + Drag&Drop + Ctrl+V の 3 種に確定

### Q3: プレビューの見せ方

| Option | Description | Selected |
|--------|-------------|----------|
| 画像はサムネ + text/code はファイル名チップ | 48×48 or 64×64 サムネ + X ボタン、text は [📄 name size ×] pill | ✓ |
| 全てファイル名チップのみ | 画像もサムネなし。実装最小だが画像確認性 ↓ | |
| 画像は大きめサムネで入力欄の上に帯状に表示 | ChatGPT 方式の 96×96 中大サムネ。垂直高増え | |

**User's choice:** サムネ + チップ → D-05

### Q4: キャンセル / エラー時の自動削除

| Option | Description | Selected |
|--------|-------------|----------|
| エラーのみ自動削除 / キャンセルは残す | ケース B = 自動削除、ケース A/C = 残す、ケース D = 手動削除 | ✓ |
| 全て自動削除（キャンセルもエラーも） | orphan 最小化だがユーザー再添付負担 | |
| 自動削除しない（thread 削除時のみ消える） | ADR-0048 のライフサイクルに一本化 | |

**User's choice:** エラーのみ自動削除 → D-06

---

## Area 3: multimodal 非対応モデル fallback

### Q1: vision 対応判定のソース

| Option | Description | Selected |
|--------|-------------|----------|
| SDK list_models() キャッシュ + /api/models endpoint | ModelInfo.capabilities.supports.vision を起動時取得 + TTL キャッシュ | ✓ |
| hardcoded allowlist | 現時点の vision 対応モデルを constants に埋め込み | |
| SDK + hardcoded fallback | SDK 失敗時 hardcoded。二重管理コスト | |

**User's choice:** SDK list_models() → D-16

### Q2: 非対応モデル選択時の UX

| Option | Description | Selected |
|--------|-------------|----------|
| 画像添付時に警告バナー + 別モデル推奨 | 📎 は active。画像添付瞬間に InputBar 上 banner + ワンクリック切替 | ✓ |
| 📎 ボタンを disabled（画像のみ） | 画像 accept フィルタを非対応モデル時 restrict。ワークフロー長い | |
| 添付自由 / 送信時 worker が判断 | UI 完全自由、送信時初めて toast | |

**User's choice:** 警告バナー → D-17

### Q3: 非対応モデルで実送信してしまった worker 側 fallback

| Option | Description | Selected |
|--------|-------------|----------|
| 画像を attachments から除外 + SystemMessage 注入 | text/code は通常送信、画像だけ drop + 「このモデル非対応」を SystemMessage で LLM に伝達 | ✓ |
| worker が緑登で拒否 + UI エラー表示 | job 実行せず error 返し。graceful とは ずれる | |
| MarkItDown で alt-text 抽出 | 画像から text 要約生成。フォールバック産出弱い | |

**User's choice:** 画像 drop + SystemMessage 注入 → D-18

### Q4: ModelVisionLimits の UI 利用

| Option | Description | Selected |
|--------|-------------|----------|
| UI で pre-validate + worker で再検証 | defense-in-depth。UI で早いフィードバック | ✓ |
| worker のみで検証 | UI は無条件に受ける。送信後初めて判明 | |
| limits 利用せず Phase 36 固定値のみ | 10MB / 5 枚を固定。モデル差無視 | |

**User's choice:** UI + worker 両方 → D-19

---

## Area 4: 履歴上の添付可視化とチェックポイント保存

### Q1: 真実のソース

| Option | Description | Selected |
|--------|-------------|----------|
| HumanMessage.additional_kwargs[attachments] (checkpoint) | LangGraph checkpointer が PG に自動永続化 | ✓ |
| thread folder の実ファイル（毎回 scan） | GET /api/threads/{id}/attachments で ls。per-turn 紐付け失われる | |
| 両方（checkpoint = per-turn / folder = 現在の手持ち） | UI ロジック複雑化 | |

**User's choice:** checkpoint → D-20

### Q2: 履歴 UI の表示位置

| Option | Description | Selected |
|--------|-------------|----------|
| メッセージバブル内の末尾にチップ行 | ChatGPT / Claude 方式。bubble 下に [📄 foo.py] [🖼 bar.png] | ✓ |
| 画像サムネ / text チップ / クリックで modal | bubble 内 + 拡大 modal。実装コスト高 | |
| スレッド単位の別パネル / ドロアー | 検索しやすいが per-turn 紐付け見えにくい | |

**User's choice:** バブル内末尾チップ行 → D-21

### Q3: GET /api/chat/history の返り値設計

| Option | Description | Selected |
|--------|-------------|----------|
| BaseMessage.additional_kwargs をそのまま返す | 既存 get_thread_messages に additional_kwargs 追加するだけ | ✓ |
| 添付は別 API (GET /api/threads/{id}/attachments) | 履歴は従来通り、添付は別エンドポイント。message 紐付け要マッピング | |
| history + 別 API 両方 | defense-in-depth だが実装量増 | |

**User's choice:** additional_kwargs 返却 → D-22

### Q4: 画像サムネ配信

| Option | Description | Selected |
|--------|-------------|----------|
| GET /api/threads/{id}/attachments/{name} で raw 配信 | JWT 認証 route、browser resize で十分、専用 thumb 不要 | ✓ |
| 専用サムネ生成 (Pillow) + キャッシュ | upload 時に 256×256 生成・.thumb/ に保存 | |
| frontend に base64 data URI を checkpoint kwargs に埋める | 肥大化で非推奨 | |

**User's choice:** raw 配信 → D-23

---

## Final confirmation

**User's choice:** 準備完了 — CONTEXT.md を作って。追加議論なし。

---

## Claude's Discretion

- upload progress UX（percent / cancel）
- DELETE endpoint の return 形式（204 / 200 + JSON）
- エラー UI パーツ（ConfirmModal 流用 / toast / inline banner）
- SystemMessage 注入文言
- /api/models キャッシュ TTL 具体値
- サムネピクセルサイズ（48 vs 64 vs 96）
- 複数タブからの同時アップロード競合制御
- Gem / SuperChat / Canvas / DebateChat の添付サポート範囲
- モバイル幅 drop zone / paste 挙動
- EXIF / メタデータサニタイズ
- MIME sniff（サーバー側）
- multipart upload size 制限実装方式
- `_astream` での attachments 対応の足並み

## Deferred Ideas

- 外部ストレージ連携 (GitHub / Drive / URL import) — 新 phase / v6.1+
- 専用サムネ生成 (Pillow) + キャッシュ — Phase 39 polish で必要なら
- EXIF メタデータサニタイズ — v6.1+
- 複数タブ同時 upload 競合 — v6.1+
- `attachments_read_bytes` tool — 不要（volume mount で足りる）
- OCR（画像テキスト抽出）— v6.1+
- 過去 turn 添付の一括パネル — 必要性が出たら
- 画像拡大 modal / viewer — Phase 38 に寄せる
