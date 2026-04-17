---
phase: 27-askuserquestion-ai-ui
verified: 2026-04-17T02:04:54Z
status: human_needed
score: 9/9
overrides_applied: 0
human_verification:
  - test: "ブラウザで AI に質問プロトコルでの応答を指示し、QuestionPanel が表示されるか確認"
    expected: "入力エリアが QuestionPanel に置き換わり、回答送信後に通常の textarea に戻る"
    why_human: "AI がプロトコルに従って <ask_user_question> タグを生成するかどうかはモデル依存。コード上の parseAUQ/条件置換ロジックは正しいが、エンドツーエンドの動作確認は実際のブラウザ操作が必要"
  - test: "ダーク/ライトテーマ切替時の QuestionPanel 表示確認"
    expected: "テーマ切替で背景色・ボーダー色・テキスト色が適切に変わる"
    why_human: "視覚的な表示確認はプログラム検証不可"
---

# Phase 27: AskUserQuestion AI-UI Verification Report

**Phase Goal:** AI エージェントが `<ask_user_question>` タグで構造化質問（single/multi/text）をユーザーに提示し、QuestionPanel UI で回答を受け取り、テキスト化して既存チャットフローに送信する対話パターンを全アプリで動作させる
**Verified:** 2026-04-17T02:04:54Z
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | LangGraph 経路（Chat/GemChat/CanvasChat）のシステムプロンプトに AUQ プロトコルが含まれる | VERIFIED | `langgraph_handler.py:77` で `effective_system_prompt` に `AUQ_PROTOCOL` を連結。`AUQ_PROTOCOL` は `system_prompt.py:23-44` で `<ask_user_question>` を含む定数 |
| 2 | Orchestrator 経路（SuperChat）のシステムプロンプトに AUQ プロトコルが含まれる | VERIFIED | `system_prompt.py:59` で `build_system_prompt_prefix` に `AUQ_PROTOCOL` を append。全 SubAgent にプレフィックスが注入される |
| 3 | QuestionPanel コンポーネントが single/multi/text の 3 質問タイプをレンダリングできる | VERIFIED | `QuestionPanel.tsx:126-202` で `text` 型は input、`single`/`multi` 型は optionGrid でレンダリング。`toggleOption` が型別に単一/複数選択を処理 |
| 4 | AskUserQuestionPayload 型が types.ts からエクスポートされる | VERIFIED | `types.ts:147-164` に `AUQOption`, `AUQQuestion`, `AskUserQuestionPayload` の 3 インターフェースが export されている |
| 5 | AI が `<ask_user_question>` タグを返したとき、チャット入力欄が QuestionPanel に置き換わる | VERIFIED | `useChat.ts:56-88` の `parseJobResult` が AUQ タグを検出、`handleResult` (line 166-168) で `setPendingQuestion`。`MessageArea.tsx:375` で `pendingQuestion ?` による条件分岐で QuestionPanel をレンダリング |
| 6 | ユーザーが質問に回答して送信すると、「質問：回答」形式のテキストが POST /api/chat に送信される | VERIFIED | `useChat.ts:322-329` の `handleQuestionSubmit` が全角コロン区切り（`${q}：${a}`）でテキスト化して `sendMessage` を呼ぶ |
| 7 | 全 5 アプリ（Chat/SuperChat/GemChat/CanvasChat/DebateChat）で QuestionPanel が動作する | VERIFIED | 全 5 ファイルで `pendingQuestion, handleQuestionSubmit` を useChat から取得し、MessageArea に `pendingQuestion={pendingQuestion}` と `onQuestionSubmit={handleQuestionSubmit}` を props 渡し |
| 8 | 質問パネル未回答時はテキスト入力欄が無効化されている | VERIFIED | `MessageArea.tsx:375-389` で `pendingQuestion` がある場合は textarea を完全に非表示にし QuestionPanel に置換（無効化ではなく非表示だが、入力を防ぐ目的は達成） |
| 9 | 回答送信後に入力欄が通常の textarea に戻る | VERIFIED | `handleQuestionSubmit` (useChat.ts:323) で `setPendingQuestion(null)` → pendingQuestion が null になり MessageArea の条件分岐で textarea が復帰 |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/utils/system_prompt.py` | AUQ_PROTOCOL 定数 + build_system_prompt_prefix 拡張 | VERIFIED | AUQ_PROTOCOL 定数 (line 23-44)、build_system_prompt_prefix に append (line 59) |
| `app/jobs/handlers/langgraph_handler.py` | effective_system_prompt に AUQ プロトコル追記 | VERIFIED | import (line 13) + 連結 (line 77) |
| `frontend/src/types.ts` | AUQ 型定義 | VERIFIED | AUQOption, AUQQuestion, AskUserQuestionPayload の 3 型が export (line 147-164) |
| `frontend/src/components/QuestionPanel.tsx` | 質問パネル UI コンポーネント | VERIFIED | parseAUQ + QuestionPanel を export。385 行、single/multi/text 対応、ダーク/ライトテーマ対応 |
| `frontend/src/hooks/useChat.ts` | pendingQuestion 状態と handleQuestionSubmit | VERIFIED | UseChatReturn に両フィールド (line 51-52)、state (line 111)、callback (line 322-329) |
| `frontend/src/components/MessageArea.tsx` | 入力エリア条件置換 | VERIFIED | QuestionPanel import (line 20)、pendingQuestion/onQuestionSubmit props (line 33-34)、条件分岐 (line 375) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| system_prompt.py | build_system_prompt_prefix | AUQ_PROTOCOL append | WIRED | line 59: `parts.append(AUQ_PROTOCOL)` |
| langgraph_handler.py | effective_system_prompt | AUQ_PROTOCOL import + concat | WIRED | line 13: import, line 77: `+ AUQ_PROTOCOL` |
| useChat.ts | MessageArea.tsx | pendingQuestion prop | WIRED | 全 5 アプリで `pendingQuestion={pendingQuestion}` を渡している |
| MessageArea.tsx | QuestionPanel.tsx | import + JSX render | WIRED | line 20: import, line 384-387: `<QuestionPanel questions={...} onSubmit={...} />` |
| useChat.ts | parseAUQ | import from QuestionPanel.tsx | WIRED | line 8: `import { parseAUQ }`, line 61/83: `parseAUQ(raw)` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| QuestionPanel.tsx | questions (props) | useChat.ts pendingQuestion | AI レスポンスの parseAUQ 結果 | FLOWING (parseJobResult -> setPendingQuestion -> MessageArea props -> QuestionPanel) |
| useChat.ts | pendingQuestion | parseJobResult -> parseAUQ | AI レスポンスから AUQ タグをパース | FLOWING (try/catch 両方で検出) |

### Behavioral Spot-Checks

Step 7b: SKIPPED (Docker 環境が必要なため、ランタイム検証は不可)

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUQ-01 | 27-01 | LangGraph 経路の system prompt に AUQ プロトコルが注入され、AI が `<ask_user_question>` タグを生成できる | SATISFIED | system_prompt.py AUQ_PROTOCOL + langgraph_handler.py で連結 |
| AUQ-02 | 27-01 | Orchestrator 経路の system prompt に AUQ プロトコルが注入され、全 SubAgent が質問可能 | SATISFIED | build_system_prompt_prefix に AUQ_PROTOCOL append |
| AUQ-03 | 27-02 | フロントエンドの parseJobResult が `<ask_user_question>` タグを検出し pendingQuestion 状態を管理する | SATISFIED | useChat.ts parseJobResult + pendingQuestion state |
| AUQ-04 | 27-02 | ユーザー回答が「質問：回答」テキスト形式で POST /api/chat に送信される | SATISFIED | handleQuestionSubmit で全角コロン区切りテキスト化 -> sendMessage |
| AUQ-05 | 27-02 | 全 5 アプリで QuestionPanel が動作する | SATISFIED | ChatApp/SuperChatApp/GemChatApp/CanvasChatApp/DebateChatApp 全てに props 伝播確認済み |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | - |

Anti-pattern scan clean. TODO/FIXME/placeholder/stub パターンは検出されなかった。

### Human Verification Required

### 1. QuestionPanel エンドツーエンド動作確認

**Test:** ブラウザで Chat アプリを開き、AI に「以下の項目について `<ask_user_question>` フォーマットで質問してください：データベースの種類、デプロイ環境」と指示する
**Expected:** 入力エリアが QuestionPanel に置き換わり、選択肢をクリックして回答送信後、通常の textarea に戻り「質問：回答」テキストが送信される
**Why human:** AI がプロトコルに従うかはモデル依存。コードのパス自体は型チェック済みだが、実際のエンドツーエンドフローはブラウザ操作が必要

### 2. ダーク/ライトテーマ表示確認

**Test:** QuestionPanel 表示中にテーマを切り替える
**Expected:** 背景色・ボーダー色・テキスト色が isDark フラグに応じて適切に変わる
**Why human:** 視覚的な色表示の正しさはプログラム検証不可

### Gaps Summary

コード実装に関する全ての must-have は VERIFIED。AUQ_PROTOCOL のバックエンド注入（LangGraph 経路 + Orchestrator 経路）、フロントエンドの型定義・QuestionPanel コンポーネント・parseAUQ パーサー、useChat hook での AUQ 検出とテキスト化送信、MessageArea の入力エリア条件置換、全 5 アプリへの props 伝播、すべてが正しく実装・接続されている。

ブラウザでのエンドツーエンド動作確認（AI がプロトコルに従うか + 視覚的表示）のみ human verification が必要。

---

_Verified: 2026-04-17T02:04:54Z_
_Verifier: Claude (gsd-verifier)_
