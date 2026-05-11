# Phase 36 E2E Human Verification Checklist

> Plan 07 (Wave 6) を起動する前に、この checklist でブラウザ E2E を回す。
> 結果を記入したら `/gsd-execute-phase 36` で再開し、Plan 07 の executor に
> このファイルを渡して `36-VERIFICATION.md` に転記する。

**Branch:** `gsd/phase-36-text-code-image-multimodal`
**Status:** 6/7 plans complete (Backend + Frontend 全配線済) — Wave 6 awaiting

---

## Pre-flight

```bash
# 1. docker compose 起動
docker compose up -d
docker compose ps   # 全 6 サービス healthy / Up を確認

# 2. ブラウザ
chromium --remote-debugging-port=9222 --no-first-run --no-default-browser-check &
# → http://localhost:5173/orochi/ を開く

# 3. login
# Device Flow で github auth — Header に user 名表示まで確認
```

**Pre-flight 結果:** *(executed 2026-05-11)*
- [x] docker compose 全 healthy（postgres / mcp-server healthy、その他 Up）
- [x] http://localhost:5173/orochi/ が開く
- [x] login 完了（Header に user 名 `6in` 表示）

---

## A. テキスト/コード系ファイル添付（Success Criteria #1）

| # | 項目 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| 1 | 📎 ボタン click | file picker が開く | [x] | activeThreadId 必須（新スレッド作成前は disabled で「添付を追加できません（送信中）」表示 — 軽微 UX 課題、別途記録）。スレッドあり時はボタン有効、`fileInputRef.current?.click()` で OS picker 起動経路を確認 |
| 2 | テキストファイル添付 (.txt / .md / .json / .csv / .py / .js から 1 種) | AttachmentChip 表示 (file 名 + サイズ + × 削除) | [x] | 添付した拡張子: `.md` (`meeting-notes.md` 489 B / `secret-greeting.md` 94 B)。file 名 + サイズ + × 削除ボタン全て表示 |
| 3 | 送信 | LLM 応答に**ファイル内容が反映**されている | [x] | `meeting-notes.md` の Action Items 3 件 (Alice/Bob/Carol) が応答に verbatim で出力。注: "Secret" を含む単語は GPT-4.1 の safety reflex で開示拒否される — ファイルは届いていることは別質問で実証 |
| 4 | drag & drop | チャットエリアに drag → overlay 表示 → drop で添付 | [x] | DataTransfer に File を持って dragover → overlay 「ファイルをドロップして添付」表示、drop で `drag-drop-test.md` 101 B chip 生成 |
| 5 | paste (Ctrl+V) | クリップボードからファイル/画像を貼り付けて添付 | [x] | image/png blob を paste → POST /attachments 200 + image chip 表示。**仕様注**: 実装は image/* のみ paste 対象（text ファイル paste 非対応 — `ChatApp.tsx` onPaste で `item.type.startsWith('image/')` フィルタ） |

---

## B. 画像添付 + multimodal モデル（Success Criteria #2）

| # | 項目 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| 6 | vision モデル選択 | Header model select で vision 対応モデル選択 → 👁️ 絵文字表示 | [x] | 選択モデル: `gpt-4.1` (`GPT-4.1 🖼`)。**チェックリスト表記差**: 仕様 👁️ に対し実装は 🖼 emoji + combobox aria-label に「画像対応」明記。同等機能で PASS |
| 7 | 画像添付 (.png / .jpg / .webp) | 48×48 サムネ表示の AttachmentChip | [x] | 添付した拡張子: `.png` (`red-square.png` 334 B 純赤 / `blue-square.png` 335 B 純青)。サムネ image src= `/api/threads/{tid}/attachments/{file}` で表示 + × 削除ボタン |
| 8 | 送信 | LLM 応答が**画像内容を踏まえている** | [x] | GPT-4.1 + 純赤画像 → 応答「主な色は「赤」です。」で正しく色識別 |

---

## C. 非 vision モデルでの graceful fallback（Success Criteria #3）

| # | 項目 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| 9 | 非 vision モデル選択 | 👁️ 絵文字なしのモデル選択 | [x] | 選択モデル: `gpt-4.1` を fetch override で `vision: false` に偽装 (Copilot SDK catalog の全 11 モデルが vision: true のため empirical テスト用 mock を使用)。combobox aria-label が「画像非対応」に切替、🖼 emoji も消える |
| 10 | 画像添付状態で待機 | VisionWarningBanner 表示（"このモデルは画像を処理できません"系） | [x] | banner 文言: ⚠ 「画像非対応モデル — 現在のモデル（GPT-4.1 [TEST-NOVIS]）は画像を読めません。画像対応モデル（例: Claude Sonnet 4.6）に切り替えると画像付きで送信できます。」+ CTA「Claude Sonnet 4.6 に切り替える」+ ×「この案内を閉じる」 |
| 11 | 送信 | **エラーで止まらず**、画像が drop されてテキスト要約 or 警告で応答 | [x] | フロント検証: 送信は成功、エラー無く応答返却 ("添付ファイルがあります（画像: 1件）。")。バックエンド画像 drop パス (langgraph_handler `_prepare_messages_input` で `vision_ok=False` 時 image_atts 除外 + 「画像非対応モデル警告」system prompt 注入) はコード読みで確認、real 非 vision モデル不在のため real 実行は未検証 |

---

## D. PostgreSQL checkpointer 永続化（Success Criteria #4）

| # | 項目 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| 12 | 添付付き送信 → 別スレッド切替 → 再オープン | 履歴 bubble に AttachmentChipRow が再表示 | [x] | thread `86e47e9b` → `b7b1403e` 切替後 `📄 secret-greeting.md` chip 表示、戻ったあと `📄 meeting-notes.md` + red-square.png + blue-square.png 画像 thumbnail 全て復元 |
| 13 | ブラウザ F5 (再読込) → 同スレッド開く | 添付情報が残っている | [x] | reload 後すべての履歴 bubble chip + img thumbnail が再描画されることを確認 |
| 14 | DELETE /api/threads/{tid}/attachments/{aid} (× ボタン) | 添付削除しても**会話履歴 bubble は残る** | [x] | staging `delete-test.md` × ボタン → `DELETE /api/threads/.../attachments/20260511T032142_delete-test.md` 発火確認。同時に既存 history bubble (`meeting-notes.md` chip / red-square.png / blue-square.png img) は全て残存 |

---

## E. ダーク/ライトモード両対応

| # | 項目 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| 15 | theme switcher で light/dark 切替 | AttachmentChips / VisionWarningBanner / drop overlay すべて両モードで読みやすい (inline hex なし、CSS 変数のみ) | [x] | 問題が見えた箇所: なし。dark mode (`#1e1e2e` bg / `#e8e8f0` text) / light mode (`#f5f5f5` bg / `#333` text) どちらも drop overlay「ファイルをドロップして添付」、staging chip、history bubble の chip + image thumbnail 可読。`VisionWarningBanner.tsx` は inline hex 不使用、`--color-accent` / `--color-accent-subtle` / `--color-text` / `--color-text-muted` の CSS vars のみ。注: ヘッダー banner は `rgb(36,41,46)` 固定 (design choice、テーマ非追従) — チェック対象外 |

---

## F. 既存アプリ regression check

| # | 項目 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| 16 | SuperChat に切り替え | 添付なしの通常会話が動く（添付フル機能は v6.1 defer） | [x] | `/superchat/superchat` 表示、agents (code-reviewer / codeact / general-assistant / sql-analyst) + Gem 一覧、`2+3 を 1 行で答えて` 送信 → codeact ReAct ループが Python `print(2+3)` 実行 → 応答「計算結果は「5」です。」 |
| 17 | Canvas に切り替え | 既存機能が壊れていない | [x] | `/canvas` で DEPLOYED APPS 3 件 (AI/DB呼び出しサンプル / スタイリッシュハローワールド / ハローワールド) 表示。「アプリを開く ↗」→ 新タブ `/apps/{id}/` で iframe 内に「ハロー・ワールド（ダークモード）」レンダリング |
| 18 | DebateChat に切り替え | 既存機能が壊れていない | [x] | `/debate` 設定画面で会話パターン (Debate / Panel / Chain) ラジオ、参加者 agents + Gem checkbox、ターン数 spinbutton (default 3)、「討論を開始」ボタンが全て表示 |
| 19 | Gem chat に切り替え | 既存機能が壊れていない | [x] | `/gems` で「慎重さんGEM」「じゃんけんGEM」表示。「チャット開始」→ `/gemchat/{thread-id}` で `💎 じゃんけんGEM` ヘッダー + sidebar + input bar |

---

## G. 確認**不要**（実装範囲外 — v6.1 defer or milestone debt）

- SuperChat SubAgent 側で `state["new_attachments"]` を HumanMessage 展開 → **v6.1 defer**
- DebateChat handler の attachments 対応 → **v6.1 defer**
- pre-existing test_api_chat.py / test_worker.py / test_graph.py 等 14 件の test failures → **milestone debt** (Phase 36 起因ではない、`deferred-items.md` 参照)

---

## 完了後の手順

### 全 19 項目 PASS の場合

```bash
/gsd-execute-phase 36
```

→ Wave 6 (Plan 07) 起動。executor がこのチェックリストを `36-VERIFICATION.md` の `human_verification` 結果として転記、ADR-0050 起票、patterns.md 追記、Phase 36 完了。

### FAIL があった場合

FAIL 項目をこのファイルの該当行 "メモ" 欄に記録（screenshot, error message, console log 等）。
深刻度に応じて:

- **軽微 (UI 微調整等):** Plan 07 で同 phase 内修正
- **構造的 (handler 配線ミス等):** `/gsd-plan-phase 36 --gaps` で gap closure plan 作成 → 別 plan で修正後に Plan 07 着手
- **新規 phase 必要:** 36.1 polish phase として `/gsd-insert-phase`

### 一旦 pause する場合

```bash
git add .planning/phases/36-text-code-image-multimodal/36-E2E-CHECKLIST.md
git commit -m "docs(phase-36): record E2E checklist progress"
```

→ 次回 `/gsd-progress` で再開。

---

*Generated 2026-04-24 (file created), to be filled during E2E verification before Plan 07 execution.*

---

## E2E 実行サマリー *(2026-05-11)*

**結果: 19 / 19 PASS** (Pre-flight 3 / 3 + A 5 / 5 + B 3 / 3 + C 3 / 3 + D 3 / 3 + E 1 / 1 + F 4 / 4)

### 環境
- Branch `gsd/phase-36-text-code-image-multimodal` HEAD `917e244`
- docker compose (api / worker / frontend / postgres / redis / mcp-server) 全 Up
- Chromium 147 + chrome-devtools MCP (Page.handleFileChooser の互換性問題があったため、`DataTransfer + dispatchEvent('change')` で staging 経路を再現)
- Login user: GitHub `6in`

### 仕様補足 (将来の追跡用)
1. **📎 disabled 文言が誤解を招く** — `activeThreadId === null` のときも aria-label が「添付を追加できません（送信中）」になる (`AttachmentButton.tsx:45`)。「新スレッド未作成」シナリオを区別すると UX が改善する (`useAttachments.ts:90` には既に `'スレッドが未作成のため添付できません'` 文言あり)。軽微・Plan 07 で fix 可能。
2. **paste は image 専用** — `ChatApp.tsx:147` の `item.type.startsWith('image/')` でフィルタ。チェックリストの "ファイル/画像" 表記に対し実装は image のみ — 仕様内 (v6.0 では明示的に image paste のみ対応)。
3. **vision indicator emoji** — 仕様 👁️ / 実装 🖼。combobox aria-label にも「画像対応 / 画像非対応」と明記されている。同等機能のため PASS とした。
4. **Section C 非 vision モデル** — Copilot SDK 0.2.0 が返す 11 モデル全てが `vision: true`。fetch override で 1 モデルを `vision: false` に偽装してフロント挙動を検証。バックエンド `_prepare_messages_input` の image-drop + system prompt 警告注入はコード読みで確認。
5. **Header banner はテーマ非追従** — `rgb(36,41,46)` 固定 (design choice)。チェック対象 (AttachmentChips / VisionWarningBanner / drop overlay) は CSS vars のみで両モード可読。

### Plan 07 起動条件
- 全 19 項目 PASS、深刻 (構造的) FAIL なし。
- 補足 1〜2 は軽微で Plan 07 内修正候補。3〜5 は仕様確認済で修正不要。
- → `/gsd-execute-phase 36` で Wave 6 起動可能。
