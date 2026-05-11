---
phase: 35
plan: 03
title: "MessageArea → InputBar 分離 + var() 移行 + isDark 三項排除"
status: draft
type: execute
wave: 1
depends_on: [01]
files_modified:
  - frontend/src/components/InputBar.tsx
  - frontend/src/components/MessageArea.tsx
autonomous: true
requirements: [UX-04]
requirements_addressed: [UX-04]
tags: [frontend, react, component-split, controlled-component, phase-36-handoff]
must_haves:
  truths:
    - "frontend/src/components/InputBar.tsx が存在し、controlled component として value/onChange/onSend/toolbarSlot/previewSlot/copyAllSlot を受け取る"
    - "MessageArea.tsx が InputBar を使い、既存の UX（typing indicator / streamPreview / QuestionPanel / resend checkbox / cancel）が retain されている"
    - "MessageArea.tsx から isDark 三項分岐が除去されている（0 件）"
    - "InputBar.tsx に isDark 三項分岐が存在しない（0 件）"
    - "InputBar の textarea 左側に toolbarSlot（空ならレンダーしない）、textarea 上に previewSlot（空ならレンダーしない）が配置される"
    - "AUQ suffix 付与ロジックは MessageArea 側に残る（InputBar に漏れない — Pitfall 4）"
  artifacts:
    - path: "frontend/src/components/InputBar.tsx"
      provides: "controlled input bar with slot reservations for Phase 36 attachments"
      exports: ["InputBar", "InputBarProps"]
      min_lines: 100
    - path: "frontend/src/components/MessageArea.tsx"
      provides: "chat view owning inputValue state + delegating to InputBar"
      contains: "import { InputBar } from './InputBar'"
  key_links:
    - from: "frontend/src/components/MessageArea.tsx"
      to: "frontend/src/components/InputBar.tsx"
      via: "import InputBar + 渡す props value/onChange/onSend/onCancel/onAskMe/isThinking/disabled/placeholder/copyAllSlot"
      pattern: "<InputBar\\s"
    - from: "InputBar.tsx textarea"
      to: "CSS 変数（Plan 01 で定義）"
      via: "inline style で var(--color-border) / var(--color-accent) 等を参照"
      pattern: "var\\(--color-"
---

<objective>
MessageArea.tsx L383-485 の chat-input-bar ブロックを **controlled コンポーネント** `InputBar.tsx` として分離し、Phase 36 の `<AttachmentButton>` / `<AttachmentChips>` 差し込みを想定した `toolbarSlot` / `previewSlot` / `copyAllSlot` 3 スロットを予約する。同時に MessageArea / InputBar 両ファイルから isDark 三項分岐を排除し、inline style を CSS 変数参照に置換する。

**Purpose:** D-08（InputBar 分離）+ D-09（toolbar textarea 左配置）+ D-01（isDark 排除）を同時に達成。Phase 36 Handoff Contract の項目 3/4/5 を満たす。

**Output:** InputBar.tsx 新規（~120 行）+ MessageArea.tsx 改修（489 → ~340 行）。既存 UX（AskMe / Cancel / Send / QuestionPanel / resend / streamPreview / typing / CopyAllButton）は全 retain。
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/35-dashboard-design-system/35-CONTEXT.md
@.planning/phases/35-dashboard-design-system/35-UI-SPEC.md
@.planning/phases/35-dashboard-design-system/35-RESEARCH.md
@.planning/phases/35-dashboard-design-system/35-PATTERNS.md
@.planning/phases/35-01-foundation-setup-SUMMARY.md
@docs/adr/0043-chat-history-content-normalization-defense-in-depth.md

<interfaces>
<!-- InputBarProps 契約 (UI-SPEC §InputBar Contract L278-309 verbatim) -->
```typescript
export interface InputBarProps {
  // 送信系
  value: string;
  onChange: (next: string) => void;
  onSend: (text: string, contextMessages?: ContextMessage[]) => void;
  onCancel?: () => void;          // thinking 中のみ有効
  onAskMe?: () => void;           // AUQ 起動（opaque callback、suffix は知らない）

  // 状態
  disabled?: boolean;
  isThinking?: boolean;           // true なら Send → Cancel 切替
  placeholder?: string;

  // スロット (Phase 36 で埋まる)
  toolbarSlot?: React.ReactNode;  // textarea 左の横並び toolbar (📎 / ModelSelector 等)
  previewSlot?: React.ReactNode;  // textarea 上の添付チップ・画像サムネ帯

  // UX 補助
  copyAllSlot?: React.ReactNode;  // 既存の CopyAllButton を差し込む枠
}
```

<!-- MessageArea に残す state (RESEARCH.md §Pitfall 8) -->
- `inputValue` (MessageArea で保持、InputBar に props 経由で渡す)
- `excludedIndices` (resend checkbox — InputBar に渡さない)
- `elapsed` (thinking 秒数 — MessageArea 側で表示)
- `streamPreview` / `currentTool` / `pendingQuestion` (既存 UX — MessageArea 側)
- `AUQ_SUFFIX` 定数 (Pitfall 4 — MessageArea 側に残す)

<!-- InputBar の内部レイアウト (UI-SPEC L311-320) -->
```
┌────────────────────────────────────────────┐
│ [copyAllSlot] (flex-end)                    │ ← 空なら帯出さない
├────────────────────────────────────────────┤
│ [previewSlot]              ← Phase 36 で埋まる: max-height 120px overflow-y auto
├────────────────────────────────────────────┤
│ [toolbarSlot]  [textarea]  [AskMe] [Send/Cancel]  ← 1 行 (desktop)
└────────────────────────────────────────────┘
```

<!-- ADR-0043 critical 挙動 — 壊してはいけない (PATTERNS.md §7 L564-570) -->
- CopyAllButton の defense-in-depth (`typeof === 'string'` + `JSON.stringify` fallback) は保持
- MarkdownMessage の string content 制約は保持
- MessageList は既存 `<div className="cs-chat-container">` 中で retain
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 01: frontend/src/components/InputBar.tsx を新規作成（controlled component + 3 slot）</name>
  <files>frontend/src/components/InputBar.tsx</files>
  <read_first>
    - frontend/src/components/MessageArea.tsx L128-199 （state + handler 既存パターン）
    - frontend/src/components/MessageArea.tsx L383-485 （chat-input-bar DOM 構造の抽出元）
    - frontend/src/types.ts （ContextMessage 型参照）
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §InputBar Contract (L272-333)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pattern 3 (L331-521)
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §1 (L38-171)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Copywriting Contract InputBar 部 (L377-383)
  </read_first>
  <action>
`frontend/src/components/InputBar.tsx` を新規作成する。内容は以下（UI-SPEC §InputBar Contract + RESEARCH.md §Pattern 3 を verbatim 参考に）:

```tsx
// frontend/src/components/InputBar.tsx
// Phase 35 (D-08): controlled input bar extracted from MessageArea.tsx.
// Reserves toolbarSlot / previewSlot for Phase 36 attachment UI (FIN-01/02).

import { useRef, type KeyboardEvent, type ReactNode } from 'react';
import type { ContextMessage } from '../types';

export interface InputBarProps {
  // 送信系
  value: string;
  onChange: (next: string) => void;
  onSend: (text: string, contextMessages?: ContextMessage[]) => void;
  onCancel?: () => void;
  onAskMe?: () => void;

  // 状態
  disabled?: boolean;
  isThinking?: boolean;
  placeholder?: string;

  // スロット (Phase 36 で埋まる)
  toolbarSlot?: ReactNode;
  previewSlot?: ReactNode;

  // UX 補助
  copyAllSlot?: ReactNode;
}

export function InputBar({
  value,
  onChange,
  onSend,
  onCancel,
  onAskMe,
  disabled,
  isThinking,
  placeholder,
  toolbarSlot,
  previewSlot,
  copyAllSlot,
}: InputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isInputDisabled = (isThinking ?? false) || (disabled ?? false);

  const handleSend = () => {
    const text = value.trim();
    if (!text || isInputDisabled) return;
    onSend(text);
    onChange('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleAskMe = () => {
    if (!onAskMe) return;
    const text = value.trim();
    if (!text || isInputDisabled) return;
    onAskMe();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  const canSend = !!value.trim() && !isInputDisabled;

  return (
    <div
      className="chat-input-bar"
      style={{
        borderTop: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        flexShrink: 0,
      }}
    >
      {copyAllSlot && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '2px 8px 0' }}>
          {copyAllSlot}
        </div>
      )}
      {previewSlot && (
        <div
          className="chat-input-preview"
          style={{ padding: '8px 12px', maxHeight: '120px', overflowY: 'auto' }}
        >
          {previewSlot}
        </div>
      )}
      <div
        className="chat-input-row"
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: 'var(--space-2)',
          padding: 'var(--space-3)',
        }}
      >
        {toolbarSlot && (
          <div
            className="chat-input-toolbar"
            style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', flexShrink: 0 }}
          >
            {toolbarSlot}
          </div>
        )}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={placeholder ?? 'Copilot に何でも聞いてみてください... (Ctrl+Enter で送信)'}
          disabled={isInputDisabled}
          rows={1}
          className="chat-textarea"
          style={{
            flex: 1,
            resize: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: '0.5rem 0.75rem',
            fontSize: '0.95rem',
            fontFamily: 'inherit',
            lineHeight: '1.5',
            outline: 'none',
            overflowY: 'auto',
            maxHeight: '160px',
            background: 'var(--color-surface)',
            color: 'var(--color-text)',
          }}
        />
        {onAskMe && !isThinking && (
          <button
            onClick={handleAskMe}
            disabled={!canSend}
            title="AUQプロトコルで回答を要求"
            className="chat-askme-btn"
            style={{
              padding: '0.5rem 0.75rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-success)',
              background: 'transparent',
              color: 'var(--color-success)',
              fontWeight: 'bold',
              fontSize: '0.8rem',
              height: '36px',
              flexShrink: 0,
              alignSelf: 'flex-end',
              cursor: canSend ? 'pointer' : 'not-allowed',
              opacity: canSend ? 1 : 0.5,
            }}
          >
            AskMe
          </button>
        )}
        {isThinking && onCancel ? (
          <button
            onClick={onCancel}
            className="chat-cancel-btn"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              background: 'transparent',
              color: 'var(--color-text-muted)',
              fontWeight: 'bold',
              fontSize: '0.9rem',
              height: '36px',
              flexShrink: 0,
              alignSelf: 'flex-end',
              cursor: 'pointer',
            }}
          >
            キャンセル
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!canSend}
            className="chat-send-btn"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: 'var(--color-accent)',
              color: 'var(--color-accent-contrast)',
              fontWeight: 'bold',
              fontSize: '0.9rem',
              height: '36px',
              flexShrink: 0,
              alignSelf: 'flex-end',
              cursor: canSend ? 'pointer' : 'not-allowed',
              opacity: canSend ? 1 : 0.5,
            }}
          >
            送信
          </button>
        )}
      </div>
    </div>
  );
}
```

**重要な制約（全て UI-SPEC / RESEARCH / PATTERNS からの verbatim 要件）:**

- **isDark 三項分岐を書かない**（D-01）: 全ての色は `var(--color-*)` 経由
- **AUQ suffix 付与を書かない**（Pitfall 4）: `onAskMe` は opaque callback として受け取る
- **slot が空なら帯を出さない**（UI-SPEC §InputBar Contract L322）: `{toolbarSlot && (...)}` のような条件レンダー
- **Send / Cancel 排他切替は InputBar 内に閉じる**（UI-SPEC L307）
- **placeholder のデフォルト日本語**（UI-SPEC §Copywriting Contract L383）: "Copilot に何でも聞いてみてください... (Ctrl+Enter で送信)"
- **Send ボタンラベル は「送信」**（UI-SPEC §Copywriting Contract L381）
- **Cancel ラベルは「キャンセル」**（UI-SPEC §Copywriting Contract L382）
- **textarea max-height 160px + auto-resize** は既存仕様踏襲
- **Ctrl+Enter / Cmd+Enter で送信** は既存仕様踏襲
- **`previewSlot` に `max-height: 120px; overflow-y: auto`** を付与（UI-SPEC §Phase 36 Handoff Contract 補足、L456）

**ContextMessage 型の扱い:** `onSend: (text: string, contextMessages?: ContextMessage[]) => void` の signature で宣言するが、**InputBar 内では contextMessages を構築しない**（MessageArea 側の責務）。InputBar は `onSend(text)` のみ呼ぶ。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run lint &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `test -f frontend/src/components/InputBar.tsx` success
    - `grep -c 'export function InputBar' frontend/src/components/InputBar.tsx` == 1
    - `grep -c 'export interface InputBarProps' frontend/src/components/InputBar.tsx` == 1
    - `grep -cE 'toolbarSlot|previewSlot|onSend' frontend/src/components/InputBar.tsx` >= 3
    - `grep -c 'copyAllSlot' frontend/src/components/InputBar.tsx` >= 2
    - `grep -cE 'isDark \?' frontend/src/components/InputBar.tsx` == 0
    - `grep -c '#7c6ff7' frontend/src/components/InputBar.tsx` == 0
    - `grep -cE '#[0-9a-fA-F]{6}' frontend/src/components/InputBar.tsx` == 0 （生 hex ゼロ）
    - `grep -c 'var(--color-accent)' frontend/src/components/InputBar.tsx` >= 1 （Send ボタン）
    - `grep -c 'var(--color-success)' frontend/src/components/InputBar.tsx` >= 1 （AskMe ボタン）
    - `grep -c '送信' frontend/src/components/InputBar.tsx` >= 1
    - `grep -c 'Copilot に何でも聞いてみてください' frontend/src/components/InputBar.tsx` == 1
    - `grep -c 'AUQ_SUFFIX\|ask_user_question' frontend/src/components/InputBar.tsx` == 0 （Pitfall 4 — AUQ suffix が漏れていない）
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
  </acceptance_criteria>
  <done>
    InputBar.tsx が controlled component として存在し、toolbarSlot/previewSlot/copyAllSlot を引数として受け付け、空の場合に帯を描画しない。全ての色・spacing が CSS 変数経由。AUQ suffix 付与ロジックは漏れていない。build/lint green。
  </done>
</task>

<task type="auto">
  <name>Task 02: MessageArea.tsx を InputBar 利用型にリファクタ + isDark 三項排除 + var() 移行</name>
  <files>frontend/src/components/MessageArea.tsx</files>
  <read_first>
    - frontend/src/components/MessageArea.tsx 全行 （489 行、特に L128-199 / L201-380 / L383-485）
    - frontend/src/components/InputBar.tsx （Task 01 で作成）
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §7 (L494-571)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pattern 3 (L466-520 — MessageArea 側の wrap)
    - docs/adr/0043-chat-history-content-normalization-defense-in-depth.md
  </read_first>
  <action>
MessageArea.tsx を以下 4 点でリファクタする。既存 UX（typing indicator / streamPreview / QuestionPanel / resend / cancel / CopyAllButton / MarkdownMessage / Mermaid / AgGrid 等）は全て retain する。

**Step A: isDark 三項分岐を削除（D-01、UX-04-6）**

現在 7 件ある `isDark ?` 三項を全て削除し、inline style を CSS 変数参照に置換する。対象:

- L128-130 付近: `const theme = useCurrentTheme(); const isDark = theme === 'dark';` → **両行削除**（`useCurrentTheme` の import も MessageArea 内の他用途がなければ削除）
- 残る `isDark ?` 三項全てを `var(--color-*)` に置換（具体値は PATTERNS.md §7 の抽出元コード参照）:
  - `isDark ? '#9090a8' : '#888'` → `var(--color-text-muted)` （thinking indicator L321-380、resend checkbox L244-254 L304-314）
  - `isDark ? '#3a3a52' : '#d1dbe3'` → `var(--color-border)`（cancel button border L339 付近）

**Step B: chat-input-bar ブロック (L383-485) を InputBar に置換**

既存の `{pendingQuestion ? (<div className="chat-input-bar">...QuestionPanel...</div>) : (既存 chat-input-bar 全体)}` 分岐を以下に書き換え:

```tsx
{pendingQuestion ? (
  <div
    className="chat-input-bar"
    style={{
      padding: '0.75rem',
      background: 'var(--color-surface)',
      borderTop: '1px solid var(--color-border)',
    }}
  >
    <QuestionPanel questions={pendingQuestion.questions} onSubmit={onQuestionSubmit!} />
  </div>
) : (
  <InputBar
    value={inputValue}
    onChange={setInputValue}
    onSend={handleSendWrapped}
    onCancel={onCancel}
    onAskMe={onAskMe ? handleAskMeWrapped : undefined}
    isThinking={isThinking}
    disabled={disabled}
    placeholder={placeholder}
    copyAllSlot={messages.length > 0 ? <CopyAllButton messages={messages} /> : undefined}
    // toolbarSlot / previewSlot は Phase 35 では未指定 (Phase 36 で差し込む)
  />
)}
```

**Step C: MessageArea に残す state + wrapped handler を追加**

MessageArea.tsx の先頭 state 宣言エリアに以下を保持（既存から変更しない）:
- `const [inputValue, setInputValue] = useState('');`
- `const [excludedIndices, setExcludedIndices] = useState<Set<number>>(new Set());`
- `const elapsed = useElapsedSeconds(isThinking);`
- `const AUQ_SUFFIX = '\n\n[回答はAUQプロトコル（<ask_user_question>フォーマット）で返してください]';`

既存の `doSend` / `handleSend` / `handleAskMe` 等のヘルパーは以下にリファクタする（または統合する）:

```tsx
// contextMessages 組み立ては MessageArea に残す（InputBar に渡さない）
const handleSendWrapped = (text: string) => {
  if (enableResend && messages.length > 0) {
    const ctxMsgs: ContextMessage[] = messages
      .filter((_, i) => !excludedIndices.has(i))
      .map((m) => ({
        role: m.role,
        content: m.content,
        ...(m.senderName ? { sender_name: m.senderName } : {}),
      }));
    onSend(text, ctxMsgs.length > 0 ? ctxMsgs : undefined);
  } else {
    onSend(text);
  }
};

// AUQ suffix 付与は MessageArea 側の責務（Pitfall 4）
const handleAskMeWrapped = () => {
  const text = inputValue.trim();
  if (!text) return;
  handleSendWrapped(text + AUQ_SUFFIX);
  setInputValue('');
};
```

**Step D: import を整理**

- `import { InputBar } from './InputBar';` を追加
- 既存 `import` の中で MessageArea が不要になったもの（例: `useCurrentTheme` が残存で他用途なければ削除）を整理
- `ContextMessage` が types から既に import されていなければ追加

**重要な制約:**

- **AUQ suffix 付与ロジック（`+ AUQ_SUFFIX`）は MessageArea に残す**（Pitfall 4 — InputBar に移植しない）
- **`excludedIndices` / `elapsed` state は MessageArea に残す**（Pitfall 8 — InputBar に持ち込まない）
- **QuestionPanel 表示中は InputBar を render しない**（既存分岐を維持 — RESEARCH.md §Pattern 3 L493-496）
- **MessageList 以上の既存構造（typing indicator / streamPreview / resend checkbox UI / currentTool 表示等）は変更しない**（ADR-0043 の MarkdownMessage / CopyAllButton 防御ガードを破壊しない）
- **`isDark` 変数の宣言自体を削除する**（宣言だけ残して三項を消すのは NG — UX-04-6 は `isDark ?` 三項 0 件が gate）
- **`#7c6ff7` / `#0366d6` / `#1e1e2e` / `#2a2a3e` 等の生 hex を MessageArea.tsx に残さない**（UX-04-5）

**参考: PATTERNS.md §7 L498-545 の抽出元コード** を必ず先に read して、どの hex がどの semantic に対応するかをマッピングしてから書き換える（片側だけ変数化するとダーク/ライト切替が壊れる — Pitfall 1）。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run lint &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'import { InputBar } from' frontend/src/components/MessageArea.tsx` == 1
    - `grep -c '<InputBar' frontend/src/components/MessageArea.tsx` >= 1
    - `grep -cE 'isDark \?' frontend/src/components/MessageArea.tsx` == 0 （UX-04-6）
    - `grep -c 'const isDark' frontend/src/components/MessageArea.tsx` == 0 （変数宣言自体を削除）
    - `grep -c '#7c6ff7' frontend/src/components/MessageArea.tsx` == 0 （UX-04-5）
    - **W-2 allowlist 明示**: `grep -E '#[0-9a-fA-F]{6}\b' frontend/src/components/MessageArea.tsx` の結果行がすべて以下のいずれかを満たす:
      - thinking indicator の `rgba(224, 82, 82, ...)` を含む行（`#e05252` の rgba 形式、thinking pulse アニメ用、**明示的に許容**）
      - もしくは 0 件（理想）
    - それ以外の 6-digit hex（特に `#7c6ff7` / `#0366d6` / `#1e1e2e` / `#2a2a3e` / `#3a3a52` / `#e8e8f0` / `#9090a8` / `#888` / `#d1dbe3` / `#22c55e` 等）は**残してはならない**
    - 具体チェック: `grep -E '#[0-9a-fA-F]{6}\b' frontend/src/components/MessageArea.tsx | grep -vE 'rgba\(224,\s*82,\s*82,' | wc -l` == 0
    - `grep -c 'AUQ_SUFFIX' frontend/src/components/MessageArea.tsx` >= 1 （Pitfall 4 — MessageArea 側に残っている）
    - `grep -c 'excludedIndices' frontend/src/components/MessageArea.tsx` >= 1 （Pitfall 8 — state 残存）
    - `grep -c 'var(--color-' frontend/src/components/MessageArea.tsx` >= 3
    - `grep -c 'QuestionPanel' frontend/src/components/MessageArea.tsx` >= 1 （既存分岐維持）
    - `grep -c 'CopyAllButton' frontend/src/components/MessageArea.tsx` >= 1 （copyAllSlot に渡している）
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
    - 手動 regression: `docker compose up` → `/orochi/chat` → テキスト入力 → Ctrl+Enter 送信 → AI 応答 → Cancel → AskMe（AUQ タグ送信）→ resend 時の「送信に含める」checkbox → QuestionPanel 表示中は InputBar 非表示、全て動作
  </acceptance_criteria>
  <done>
    MessageArea.tsx が InputBar 利用型にリファクタされ、isDark 三項・生 hex が排除された。既存 UX 全て retain（Ctrl+Enter / AUQ / resend / cancel / QuestionPanel / CopyAllButton / streamPreview / thinking indicator）。build/lint green、docker compose で手動 regression 確認完了。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MessageArea (owner of state) ↔ InputBar (controlled consumer) | InputBar は `onAskMe: () => void` opaque callback のみ知る。AUQ suffix は MessageArea 側で付与され、InputBar に漏れない。 |
| user input textarea ↔ onSend callback | textarea の value は既存仕様どおり trim して送信。特殊文字エスケープは chatscope / Markdown Layer に委譲（既存仕様）。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-11 | Information Disclosure | AUQ suffix 漏れ（Pitfall 4）— AskMe が Canvas / Debate アプリで誤発火すると、AUQ プロトコルを要求する意図せぬプロンプトが送信される | mitigate | Task 01 acceptance で InputBar に `AUQ_SUFFIX` / `ask_user_question` 文字列が存在しないことを grep で確認。Task 02 acceptance で MessageArea 側に AUQ_SUFFIX が残っていることを確認。AskMe ボタンは `onAskMe` prop が渡された時のみ描画される（`{onAskMe && !isThinking && (...)}`）ので、Canvas/Debate 側が onAskMe を渡さなければボタンが出ない。 |
| T-35-12 | Tampering | resend の contextMessages 組み立てロジックが InputBar に移動して壊れる（Pitfall 8） | mitigate | Task 02 action で `handleSendWrapped` 内に contextMessages 組み立てを明示。acceptance で MessageArea に `excludedIndices` と `AUQ_SUFFIX` が残ることを grep 確認。manual regression でチェックボックス動作確認。 |
| T-35-13 | DoS | InputBar の onSend 呼び出し後 textarea が reset されず無限送信される | mitigate | `onSend(text); onChange(''); textarea height 'auto'` の 3 操作が handleSend に含まれる。既存 MessageArea の reset 挙動を踏襲。 |
| T-35-14 | Elevation of Privilege | — | accept | frontend 内のみ、backend 権限昇格なし。 |
| T-35-15 | Repudiation | — | accept | 既存 stdout JSONL trace に影響なし（chat POST は既存 API）。 |

すべて LOW severity。security_enforcement 閾値は high のみなので block しない。
</threat_model>

<verification>
- `cd frontend && bun run lint && bun run build` 両方 exit 0
- `grep -cE 'isDark \?' frontend/src/components/{MessageArea,InputBar}.tsx` == 0（両ファイル合計 0）
- `grep -c '#7c6ff7' frontend/src/components/{MessageArea,InputBar}.tsx` == 0（両ファイル合計 0）
- `test -f frontend/src/components/InputBar.tsx`
- 手動 regression: `/orochi/chat` で Ctrl+Enter / AskMe / Cancel / QuestionPanel / resend 全動作
- 目視: dark/light toggle で InputBar 内 textarea / Send ボタン / cancel ボタン色が瞬時に切り替わる
</verification>

<success_criteria>
- Phase 36 Handoff Contract #3 / #4 / #5 達成（InputBar 存在、toolbarSlot/previewSlot reserved、MessageArea UX retain）
- UX-04-5 / UX-04-6 / UX-04-7 grep gate が MessageArea / InputBar 両ファイルで green
- AUQ suffix 付与は MessageArea に閉じられ、InputBar は AUQ の存在を知らない設計
- Phase 36 が `<InputBar toolbarSlot={<AttachmentButton />} previewSlot={<AttachmentChips />} />` として差し込むだけで動く
</success_criteria>

<output>
完了後、`.planning/phases/35-dashboard-design-system/35-03-messagearea-inputbar-split-SUMMARY.md` に以下を記録:
- InputBar.tsx 行数
- MessageArea.tsx before/after 行数
- 削除した isDark 三項の件数 (7 → 0)
- 置換した hex の件数
- 手動 regression 結果（6 機能: 送信/AUQ/resend/cancel/QuestionPanel/CopyAll）
</output>
