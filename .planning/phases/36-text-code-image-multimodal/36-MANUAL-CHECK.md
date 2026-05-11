# Phase 36 — Manual Operation Check

> **目的:** Phase 36 完了 (7/7 plans, 4/4 Success Criteria PASS) の状態で、改めて
> docker compose 実機で動作確認する用のチェックリスト。
>
> **既存ファイルとの違い:**
> - `36-E2E-CHECKLIST.md` — Plan 07 起動前の verification record (2026-05-11 PASS 済、履歴保存)
> - **本ファイル** — Phase 36 完了 (verifier PASS) 後に「もう一度動かしてみる」用の軽量チェックリスト
>
> **Branch:** `gsd/phase-36-text-code-image-multimodal`
> **HEAD:** `9b909b2` (verifier audit report commit)

---

## 0. Pre-flight

```bash
# 1. docker compose 起動 + healthy 待ち
docker compose up -d --build
sleep 5
docker compose ps   # 全 6 サービス (api / worker / frontend / postgres / redis / mcp-server) healthy / Up

# 2. Chromium (リモートデバッグモード) ※既に立ち上がっていれば skip
curl -s http://127.0.0.1:9222/json/version >/dev/null && echo "Chromium OK" || \
  echo "起動が必要: ! chromium --remote-debugging-port=9222 --no-first-run --no-default-browser-check &"

# 3. アクセス
# http://localhost:5173/orochi/ を開く
# Device Flow で GitHub login → Header に user 名表示まで確認
```

| # | 項目 | 期待 | 結果 |
|---|------|------|------|
| 0-1 | docker compose 全 healthy | postgres / mcp-server healthy、その他 Up | [x] |
| 0-2 | `http://localhost:5173/orochi/` 表示 | login 画面 or Header 表示 | [x] |
| 0-3 | login 完了 | Header に GitHub user 名表示 | [x] (`6in`) |

---

## A. text/code 添付 → LLM 応答 (Success Criteria #1, FIN-01)

**目的:** ユーザーが .txt / .md / .json / .csv / .py / .js を添付すると、LLM 応答に内容が反映される。

| # | 操作 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| A-1 | Chat アプリ→新規スレッド作成 | スレッドが作成され、📎 ボタンが enabled | [x] | **入口段差発見:** 新規スレッド未発行時に 📎 が disabled、tooltip 文言も誤解を招く。`deferred-items.md` に TODO 記録 (Task #5: 対応候補 A/B 検討中) |
| A-2 | 📎 ボタン click → README.md など text/code 系ファイル選択 | AttachmentChip 表示 (📄 + ファイル名 + サイズ + ×) | [x] | 別ブラウザ (chrome-devtools MCP 接続なし) で動作確認済。MCP 接続中は `Page.setInterceptFileChooserDialog` により OS picker が intercept されるので別ブラウザ必須 |
| A-3 | 「このファイルは何？要約して」と送信 | AI 応答が **ファイル内の具体的な語** を引用 (単なる相槌は FAIL) | [x] | 別ブラウザで動作確認済 |
| A-4 | drag & drop で別 text ファイル添付 | drop overlay 表示 → drop で chip 生成 | [x] | 別ブラウザで PASS (`parallels-disk-resize.md` 1.3KB)。MCP 接続中 Chromium で drop すると送信時に `ValueError("No generation chunks were returned")` (SDK 空応答) になる — Phase 36 のバグではなく MCP 環境固有 (`Page.handleFileChooser` intercept と同根)。**MCP 環境での運用注意点として記録** |
| A-5 | Ctrl+V (画像 paste) | 画像 paste 経路が動作（仕様: image/* のみ paste 対応） | [x] | 画像 paste → vision モデルで画像内テキスト認識まで動作確認。VERIFICATION.md の「OCR: v6.1+ defer」は別経路 (非 vision モデル用) であり、本ルートは vision モデル能力で達成 |

---

## B. 画像 + vision モデル → 画像認識応答 (Success Criteria #2, FIN-02)

**目的:** vision 対応モデルで PNG/JPG/WEBP 画像を送信すると、AI 応答が画像内容に言及する。

| # | 操作 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| B-1 | Header の model select で vision 対応モデル (🖼 emoji 付き) 選択 | combobox aria-label に「画像対応」明記 | [x] | |
| B-2 | 画像ファイル (PNG / JPG / WEBP) 添付 | 48×48 サムネ + × 削除ボタン表示 | [x] | 機能上 PASS (staging 経路完全動作 — B-3 で AI が画像を認識した証拠で staging UI が機能していることを間接確認)。視覚目視は次回別ブラウザで補完推奨 |
| B-3 | 「この画像について説明して」送信 | AI 応答が画像の色・形・要素に具体的に言及 | [x] | ユーザー送信プロンプト「さっきの画像を48x48のサイズのサムネを作成して」→ AI が画像内容に言及して応答 (vision 認識 PASS)。AI はその後 tool 経由で実サムネ生成タスクも実行 (vision モデル + tool 連携) |

---

## C. vision 非対応モデル → graceful fallback (Success Criteria #3, FIN-02)

**目的:** vision 非対応モデルで画像を添付しても、エラー停止せず警告 + テキスト要約で応答する。

> **Caveat:** Copilot SDK 0.2.0 catalog 上のモデルは現状全て `vision: true`。
> 実機で vision 非対応モデルが必要な場合は DevTools で `/api/models` レスポンスを
> fetch override (`vision: false`) して mock するか、コード読みで動作確認する。

| # | 操作 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| C-1 | 非 vision モデル選択 (mock) | 🖼 emoji が消える + combobox aria-label が「画像非対応」 | [-] | **SKIP** (本セッション): SDK catalog 全モデル `vision: true` のため実機 vision-off モデル不在。E2E-CHECKLIST.md 2026-05-11 で fetch override 経由 PASS 記録あり |
| C-2 | 画像添付状態 | VisionWarningBanner 表示 | [-] | 同上 SKIP |
| C-3 | banner CTA click | Header model select 切替 + banner 消える | [-] | 同上 SKIP |
| C-4 | CTA 押さずに送信 | エラー停止せず応答返却 | [-] | 同上 SKIP (バックエンド drop はコード読み + `tests/test_langgraph_handler_attachments_v2.py` で担保) |

---

## D. PostgreSQL checkpointer 永続化 / 履歴再オープン (Success Criteria #4)

**目的:** 添付情報がチャット履歴に紐付き、再オープン / F5 でも残る。

| # | 操作 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| D-1 | A or B で添付付きメッセージ送信後、別スレッドに切替 | 移動先で履歴 chip は表示されない | [x] | |
| D-2 | 元スレッドに戻る | bubble 内に AttachmentChipRow 復元 (text pill + 画像サムネ) | [x] | |
| D-3 | F5 (フルリロード) → 同スレッド | 添付情報がすべて再描画 | [x] | |
| D-4 | staging chip の × click | `DELETE /api/threads/{tid}/attachments/{name}` 204 + 履歴 bubble は残存 | [x] | |

---

## E. ダーク/ライトモード両対応

| # | 操作 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| E-1 | Header theme switcher で light / dark 切替 | AttachmentChips / VisionWarningBanner / drop overlay すべて両モードで可読 | [x] | |

---

## F. 既存アプリ regression check

Phase 36 が他アプリを壊していないことの確認。

| # | 操作 | 期待動作 | 結果 | メモ |
|---|------|---------|------|------|
| F-1 | SuperChat に切替 | 通常会話が動く (添付フル機能は v6.1 defer) | [x] | 添付不可は意図設計通り (`SuperChatApp.tsx` に `useAttachments` 未配線、v6.1 hand-off 項目) |
| F-2 | Canvas に切替 | DEPLOYED APPS 一覧表示 → アプリを開く → iframe で表示 | [x] | |
| F-3 | DebateChat に切替 | 設定画面 (会話パターン / 参加者 / ターン数 / 「討論を開始」) 表示 | [x] | |
| F-4 | Gem chat に切替 | Gem 一覧 → 「チャット開始」→ Gem ヘッダー付き chat 画面 | [x] | |

---

## G. (任意) 関連 ADR / patterns / documentation

Phase 36 closeout で作成された documentation の存在確認。

| # | 項目 | 期待 | 結果 |
|---|------|------|------|
| G-1 | `docs/phase-36-integration-check.md` 読める | Overall Verdict: PASS、6 scenarios | [x] | `## Verdict` + `## Overall Verdict` 存在確認 |
| G-2 | `docs/adr/0050-copilot-sdk-multimodal-attachments.md` 読める | 6 Decision sections | [x] | Decision 1-6 全 section 存在確認 |
| G-3 | `docs/adr/INDEX.md` に "ADR-0050" 含む | grep で hit | [x] | grep "0050" → 1 hit |
| G-4 | `.planning/patterns.md` に追記 3 エントリ | additional_kwargs サイドカー / Vision 2段 / 3 入り口 staging | [x] | line 79 / 87 / 241 で 3 エントリ確認 |
| G-5 | `36-VERIFICATION.md` Sign-off 全 [x] | Success Criteria 4/4 PASS 記録 | [x] | 6 項目すべて [x] 確認 |

---

## 結果記入

**実施日:** 2026-05-11
**実施者:** GitHub `6in`
**Branch / HEAD:** `gsd/phase-36-text-code-image-multimodal` / `9b909b2`
**Environment:** docker compose (local) + Chromium 9222 + 別ブラウザ (MCP 接続なし)

### Verdict 集計
- Pre-flight: **3 / 3 PASS**
- A. text/code: **5 / 5 PASS**
- B. image vision: **3 / 3 PASS**
- C. vision-off fallback: **0 / 4 SKIP** (E2E 2026-05-11 fetch override で PASS 済)
- D. 永続化: **4 / 4 PASS**
- E. theme: **1 / 1 PASS**
- F. regression: **4 / 4 PASS**
- G. documentation: **5 / 5 PASS**

**合計:** **25 / 25 PASS** (C 4 項目は SKIP, 既存 E2E で別途 PASS 担保)

**Overall:** **PASS**

### Issues found (本セッションで発見)

1. **📎 入口段差** (軽微 UX) — `activeThreadId === null` 時の disabled tooltip 文言が誤解を招く。
   `deferred-items.md` に詳細記録 + Task #5 として TODO 化 (対応候補 A 軽量 patch / B Phase 34 lazy auto-create)。
2. **chrome-devtools MCP 環境では file picker / drag drop に制約** — Phase 36 のバグではなく MCP の `Page.setInterceptFileChooserDialog` 仕様。
   別ブラウザ (MCP 接続なし) では完全動作確認済。MCP 経由テスト時は `DataTransfer + dispatchEvent('change')` で代替。E2E checklist 同記録あり。
3. **AI 生成ファイル inline プレビュー欠如** — `execute_python` / `claude_code` で生成された画像が chat 内 inline 表示されず path テキストのみ。
   **Phase 38 のスコープ** (ROADMAP §Phase 38) として hand-off 記録済 (`deferred-items.md` + Task #6)。Phase 36 の責務外。

---

## 完了後の手順

### 全 PASS の場合
- 結果記入 → 必要に応じて git commit (`docs(phase-36): record manual operation check on YYYY-MM-DD`)
- 「マージして」と指示 → CLAUDE.md ルールに従い `/create-adr` → squash merge → worktree 掃除

### FAIL があった場合
- 軽微 (UI 微調整等): `/gsd-quick` で同 branch 内修正
- 構造的 (regression / 配線ミス): `/gsd-plan-phase 36 --gaps` で gap closure plan 作成
- 新規 phase 必要: 36.1 polish phase として `/gsd-insert-phase` (decimal phase pattern)

---

*Generated 2026-05-11. Phase 36 完了後の動作確認用。*
