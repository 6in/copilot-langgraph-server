# Phase 35: ダッシュボード化 + レスポンシブ/デザイン統一 - Pattern Map

**Mapped:** 2026-04-23
**Files analyzed:** 9 (4 新規 + 5 大幅改修)
**Analogs found:** 9 / 9

参照した既存コード（absolute path）:
- `/home/parallels/workspaces/copilot-langgraph/frontend/src/theme.css` (397 行)
- `/home/parallels/workspaces/copilot-langgraph/frontend/src/components/MenuScreen.tsx` (296 行)
- `/home/parallels/workspaces/copilot-langgraph/frontend/src/components/MessageArea.tsx` (489 行)
- `/home/parallels/workspaces/copilot-langgraph/frontend/src/components/ThreadSidebar.tsx` (498 行)
- `/home/parallels/workspaces/copilot-langgraph/frontend/src/components/Header.tsx` (208 行)
- `/home/parallels/workspaces/copilot-langgraph/frontend/src/components/ConfirmModal.tsx` (97 行)
- `/home/parallels/workspaces/copilot-langgraph/frontend/src/types.ts` (164 行)
- `/home/parallels/workspaces/copilot-langgraph/frontend/src/utils/agentColor.ts` (29 行)
- `/home/parallels/workspaces/copilot-langgraph/scripts/install-hooks.sh` (61 行)

---

## File Classification

| 新規/改修ファイル | Role | Data Flow | Closest Analog | Match Quality |
|------------------|------|-----------|----------------|---------------|
| `frontend/src/components/InputBar.tsx` (新規) | component (controlled input) | request-response (onSend callback) | `frontend/src/components/MessageArea.tsx` L383-485 (chat-input-bar block) | exact (extraction) |
| `frontend/src/components/RecentThreadCard.tsx` (候補、planner 判断) | component (card button) | event-driven (onClick) | `frontend/src/components/MenuScreen.tsx` L249-296 (FeatureCard) | exact |
| `frontend/src/utils/threadGroups.ts` (新規) | utility (pure fn) | transform (date→group string) | `frontend/src/components/ThreadSidebar.tsx` L61-86 (`getDateGroup` + `groupThreads`) | exact (extraction) |
| `scripts/check-phase-35.sh` (新規) | script (grep harness) | batch / static-check | `scripts/install-hooks.sh` (bash, set -euo pipefail, heredoc, grep 判定) | role-match (bash/grep 構成) |
| `frontend/src/theme.css` (大幅改修) | config (stylesheet, tokens + @media) | — | 自身 L82-296 (既存 `[data-theme="dark"] .cs-*` + app-class override 群) | exact (migrate-in-place) |
| `frontend/src/components/MenuScreen.tsx` (再構築) | component (dashboard screen) | request-response (getApps) + transform (sort/slice threads) | 自身 L46-211 (既存カード grid) + `MessageArea.tsx` の section 分離パターン | exact (refactor-in-place) |
| `frontend/src/components/MessageArea.tsx` (改修) | component (chat view) | streaming + request-response | 自身 L201-488 (既存 textarea block が InputBar へ) | exact (extract-child-component) |
| `frontend/src/components/ThreadSidebar.tsx` (改修) | component (sidebar + drawer) | CRUD (threads) + event-driven (drawer open) | 自身 L148-498 (既存 collapse + `ConfirmModal` 呼び出し) | exact (augment-in-place) |
| `frontend/src/components/Header.tsx` (改修) | component (app header + nav) | event-driven (select / logout) | 自身 L69-207 (既存 flex 横並び) | exact (augment-in-place) |

---

## Pattern Assignments

### 1. `frontend/src/components/InputBar.tsx` (新規 controlled component)

**Analog:** `frontend/src/components/MessageArea.tsx` L128-199, L383-485
**理由:** 既存 chat-input-bar ブロック（textarea / AskMe / Send / AUQ suffix / Ctrl+Enter / auto-resize）をそのまま切り出す。RESEARCH.md §Pattern 3 参照。

**抽出元: state + handler の責務境界 (MessageArea.tsx L128-199)**
```tsx
// L128-137: state 宣言
export function MessageArea({ messages, isThinking, ... onCancel, disabled = false, placeholder, ...}: MessageAreaProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';            // ← 削除対象 (D-01)
  const [inputValue, setInputValue] = useState('');   // ← MessageArea に残す (Pitfall 8)
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isInputDisabled = isThinking || disabled;     // ← InputBar に移管可
  ...
  const elapsed = useElapsedSeconds(isThinking);      // ← MessageArea に残す
  const [excludedIndices, setExcludedIndices] = useState<Set<number>>(new Set());  // ← MessageArea に残す (Pitfall 8)

// L154: AUQ suffix 定数 — MessageArea に残す (Pitfall 4)
  const AUQ_SUFFIX = '\n\n[回答はAUQプロトコル（<ask_user_question>フォーマット）で返してください]';

// L156-173: doSend — contextMessages 組み立てを残す
  const doSend = (text: string) => {
    if (enableResend && messages.length > 0) {
      const ctxMsgs: ContextMessage[] = messages
        .filter((_, i) => !excludedIndices.has(i))
        .map((m) => ({ role: m.role, content: m.content,
          ...(m.senderName ? { sender_name: m.senderName } : {}),
        }));
      onSend(text, ctxMsgs.length > 0 ? ctxMsgs : undefined);
    } else {
      onSend(text);
    }
    setInputValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };
```

**抽出元: Ctrl+Enter + auto-resize (MessageArea.tsx L187-199)**
```tsx
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
```

**抽出元: chat-input-bar DOM 構造 (MessageArea.tsx L384-485)**
```tsx
// L384-387: 外枠 (InputBar 最外側になる)
<div className="chat-input-bar" style={{
  borderTop: '1px solid #d1dbe3',       // ← 'var(--color-border)'
  background: '#fff',                    // ← 'var(--color-surface)'
  flexShrink: 0,
}}>

// L405-409: 既存 CopyAllButton 配置 (→ copyAllSlot へ)
  {messages.length > 0 && (
    <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '2px 8px 0' }}>
      <CopyAllButton messages={messages} />
    </div>
  )}

// L410-415: textarea 行の flex row (toolbarSlot はここの先頭に差し込む — D-09)
  <div style={{
    display: 'flex',
    alignItems: 'flex-end',
    gap: '0.5rem',          // ← 'var(--space-2)'
    padding: '0.6rem 0.75rem',  // ← 'var(--space-3)'
  }}>

// L416-439: textarea 本体
    <textarea ref={textareaRef} value={inputValue}
      onChange={(e) => setInputValue(e.target.value)}
      onKeyDown={handleKeyDown} onInput={handleInput}
      placeholder={placeholder ?? 'Ask Copilot anything... (Ctrl+Enter to send)'}
      disabled={isInputDisabled} rows={1}
      className="chat-textarea"
      style={{
        flex: 1, resize: 'none',
        border: '1px solid #d1dbe3',  // ← var(--color-border)
        borderRadius: '6px',           // ← var(--radius-md)
        padding: '0.5rem 0.75rem',
        fontSize: '0.95rem', fontFamily: 'inherit', lineHeight: '1.5',
        outline: 'none', overflowY: 'auto', maxHeight: '160px',
      }}
    />

// L440-460: AskMe ボタン (--color-success 枠)
    <button onClick={handleAskMe} disabled={!inputValue.trim() || isInputDisabled}
      title="AUQプロトコルで回答を要求"
      style={{
        padding: '0.5rem 0.75rem',
        borderRadius: '6px',
        border: `1px solid ${isDark ? '#2a4a2a' : '#22c55e'}`,  // ← 1 枚化: 'var(--color-success)'
        background: 'transparent',
        color: '#22c55e',                                        // ← 'var(--color-success)'
        fontWeight: 'bold', fontSize: '0.8rem',
        height: '36px', flexShrink: 0, alignSelf: 'flex-end',
        ...
      }}>AskMe</button>

// L461-481: Send ボタン
    <button onClick={handleSend} disabled={!inputValue.trim() || isInputDisabled}
      className="chat-send-btn"
      style={{
        padding: '0.5rem 1rem',
        borderRadius: '6px',      // ← var(--radius-md)
        border: 'none',
        background: '#0366d6',    // ← 'var(--color-accent)' (UI-SPEC Accent reserved-for #1)
        color: '#fff',            // ← 'var(--color-accent-contrast)'
        fontWeight: 'bold', fontSize: '0.9rem',
        height: '36px', flexShrink: 0, alignSelf: 'flex-end',
        ...
      }}>Send</button>   // ← 日本語化: 送信
```

**Slot 配置契約 (UI-SPEC 内部レイアウト + RESEARCH.md §Pattern 3 L337-464):**
- `previewSlot` は textarea 行の上 (Phase 36 で AttachmentChips 差し込み)。空なら帯出さない。`max-height: 120px; overflow-y: auto` を InputBar 側で付与 (UI-SPEC §Phase 36 Handoff Contract 補足)。
- `toolbarSlot` は textarea 左 (D-09, ChatGPT/Claude メンタルモデル)。空なら出さない。
- `copyAllSlot` は 最上段 flex-end (既存 CopyAllButton を差し込む)。

**Validation & Error 契約:**
- `pendingQuestion` 分岐 (MessageArea.tsx L389-402 の QuestionPanel 表示) は **MessageArea 側に残す**。InputBar はそもそも render されない。
- AUQ suffix 付与は MessageArea 側 (Pitfall 4 — InputBar は `onAskMe: () => void` opaque callback のみ知る)。
- `isThinking` で Send/Cancel 排他切替は InputBar 内に閉じる (UI-SPEC L307)。

---

### 2. `frontend/src/components/RecentThreadCard.tsx` (候補、planner 判断)

**Analog:** `frontend/src/components/MenuScreen.tsx` L238-296 (FeatureCard)

**抽出元: button-based clickable card pattern (MenuScreen.tsx L259-296)**
```tsx
function FeatureCard({ icon, title, description,
  cardBg, cardBorder, textColor, subtitleColor, onClick,
}: FeatureCardProps) {
  return (
    <button
      onClick={onClick}
      style={{
        background: cardBg,                // ← 'var(--color-surface)'
        border: `1px solid ${cardBorder}`, // ← '1px solid var(--color-border)'
        borderRadius: '12px',              // ← 'var(--radius-lg)'
        padding: '1.5rem',                 // ← 'var(--space-6)'
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'box-shadow 0.2s, transform 0.1s',
        color: textColor,                  // ← 'var(--color-text)'
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 4px 16px rgba(0,0,0,0.18)';
        (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLButtonElement).style.boxShadow = 'none';
        (e.currentTarget as HTMLButtonElement).style.transform = 'none';
      }}
    >
      <div aria-hidden="true" style={{ fontSize: '2rem', marginBottom: '0.75rem', lineHeight: 1 }}>
        {icon}
      </div>
      <div style={{ fontWeight: 600, fontSize: '1rem', marginBottom: '0.5rem' }}>{title}</div>
      <div style={{ fontSize: '0.85rem', color: subtitleColor, lineHeight: 1.4 }}>{description}</div>
    </button>
  );
}
```

**差分 (RESEARCH.md §Code Example 3 L857-888):**
- icon = アプリアイコン絵文字 (ThreadInfo.app_id から解決、`frontend/src/types.ts` L37-42)
- title = `thread.label` (truncate 1 行)
- description → date group label (`getDateGroup(thread.updated_at)`, `--font-caption` + `--color-text-muted`)
- **focus ring 追加** (UI-SPEC §Visual Accessibility Baseline):
  `:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }` — Phase 35 新規ボタンで共通。
- onMouseEnter の box-shadow 値 `'0 4px 16px rgba(0,0,0,0.18)'` は primitive として残すか `var()` 化するかは planner 判断。色値そのものは ADR-0040 推奨値。

**Routing 契約 (RESEARCH.md §Example 3 L934-942 + types.ts L37-42):**
- `ThreadInfo` 型には `app_id?` はあるが `gem_id` フィールドは**無い** (types.ts 確認済み、Pitfall A1 部分解消)。
- よって MenuScreen 側で app_id → route 解決。gem スレッドは Phase 35 scope では dedicated routing は planner 判断 (例えば `app_id === 'gem'` なら GemsScreen 経由で遷移、等)。

---

### 3. `frontend/src/utils/threadGroups.ts` (新規 utility)

**Analog:** `frontend/src/components/ThreadSidebar.tsx` L61-86

**抽出元: 完全コピーして export に直す (ThreadSidebar.tsx L61-86)**
```tsx
// Group threads by date
type DateGroup = '今日' | '昨日' | '今週' | '先週' | 'それ以前';
const groupOrder: DateGroup[] = ['今日', '昨日', '今週', '先週', 'それ以前'];

function getDateGroup(updatedAt?: string | null): DateGroup {
  if (!updatedAt) return 'それ以前';
  const now = new Date();
  const updated = new Date(updatedAt);
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffMs = todayStart.getTime() - new Date(updated.getFullYear(), updated.getMonth(), updated.getDate()).getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 0 || diffDays === 0) return '今日';
  if (diffDays === 1) return '昨日';
  if (diffDays <= 7) return '今週';
  if (diffDays <= 14) return '先週';
  return 'それ以前';
}

function groupThreads(threads: ThreadInfo[]): Map<DateGroup, ThreadInfo[]> {
  const groups = new Map<DateGroup, ThreadInfo[]>();
  for (const thread of threads) {
    const group = getDateGroup(thread.updated_at);
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(thread);
  }
  return groups;
}
```

**移行手順:**
1. `frontend/src/utils/threadGroups.ts` を新規作成し、`DateGroup` / `groupOrder` / `getDateGroup` / `groupThreads` を `export` で公開。
2. `ThreadSidebar.tsx` L61-86 を削除し `import { getDateGroup, groupThreads, groupOrder, type DateGroup } from '../utils/threadGroups';` に置換。
3. `MenuScreen.tsx` からも同 import して RecentThreadCard で使用。
4. ADR-0040「スレッドサイドバー日付グループ」(Frontend・UI セクション) を破壊せず、2 箇所で複製する Pitfall を防ぐ (RESEARCH.md §Example 4 L966)。

**アナログ utility pattern:** `frontend/src/utils/agentColor.ts` が `export function` + 純粋関数 + 不変定数配列の既存 utils スタイル（`AGENT_PALETTES`, `hashName`, `agentBgColor`）。同じ構造で書く。

---

### 4. `scripts/check-phase-35.sh` (新規 grep harness)

**Analog:** `scripts/install-hooks.sh` L1-61

**抽出元: bash script preamble + heredoc + grep 判定 (install-hooks.sh L1-40)**
```bash
#!/usr/bin/env bash
# scripts/install-hooks.sh — リポジトリローカル git hook を .git/hooks/ にインストールする
#
# 用途: 新規クローン後に 1 回実行する。CLAUDE.md の運用ルールでも呼ばれる。

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

# 判定ロジックのひな形 (install-hooks.sh L28-40)
if echo "$STAGED_FILES" | grep -qE '^docs/adr/[0-9]{4}-.*\.md$'; then
  echo "[pre-commit] docs/adr/ 変更を検知 → INDEX.md を再生成"
  python3 "$REPO_ROOT/scripts/generate_adr_index.py"
  git add "$REPO_ROOT/docs/adr/INDEX.md"
fi
```

**適用パターン:**
- preamble: `#!/usr/bin/env bash` + 日本語 header + `set -euo pipefail`
- `REPO_ROOT="$(git rev-parse --show-toplevel)"` で絶対パス基準に
- 各 grep 項目を `check_X` 関数化、失敗なら `echo "FAIL: ..."` + `exit 1` で中断
- `grep -c` の結果を `[ "$count" -ge N ]` で判定、全 PASS で `echo "All checks passed"`

**本 script の 7 項目 (RESEARCH.md §Validation Architecture L1099-1110):**
| Check | Command | Expected |
|-------|---------|----------|
| UX-03-1 | `grep -c 'aria-labelledby="section-' frontend/src/components/MenuScreen.tsx` | ≥ 3 |
| UX-03-2 | `grep -n 'slice(0, 5)' frontend/src/components/MenuScreen.tsx` | ≥ 1 |
| UX-03-3 | `grep -cE 'アプリケーション\|最近のスレッド\|その他' frontend/src/components/MenuScreen.tsx` | ≥ 3 |
| UX-04-1 | `grep -cE '^\s*--color-(bg\|surface\|border\|text\|accent\|destructive\|success\|header)' frontend/src/theme.css` | ≥ 13 |
| UX-04-2 | `[data-theme="dark"]` ブロック内の semantic override count | ≥ 9 |
| UX-04-3/4 | `grep -c '@media (max-width: 1024px)'` / `767px` | ≥ 1 each |
| UX-04-5 | `#7c6ff7` hardcode 件数 @ 4 対象 tsx | 0 |
| UX-04-6 | `isDark ?` 三項 @ 4 対象 tsx | 0 |
| UX-04-7 | InputBar.tsx 存在 + toolbarSlot/previewSlot/onSend 各 1 件以上 | — |

CI 統合なし、phase gate 直前に手動 1 回実行 (RESEARCH.md §Wave 0 Gaps L1126)。

---

### 5. `frontend/src/theme.css` (大幅改修 — tokens + @media 追加 + hex→var())

**Analog:** 自身 L82-296 の既存 chatscope + app-class `!important` override ブロック群

**抽出元: chatscope container overrides (theme.css L82-95)**
```css
[data-theme="dark"] .cs-main-container,
[data-theme="dark"] .cs-chat-container,
[data-theme="dark"] .cs-message-list {
  background: #1e1e2e !important;       /* ← background: var(--color-bg) !important; */
  border-color: #3a3a52 !important;      /* ← border-color: var(--color-border) !important; */
  color: #e8e8f0 !important;             /* ← color: var(--color-text) !important; */
}

[data-theme="dark"] .cs-sidebar--left {
  background: #2a2a3e !important;        /* ← var(--color-surface) */
  border-color: #3a3a52 !important;
  color: #e8e8f0 !important;
}
```

**抽出元: ThreadSidebar app-class override (theme.css L119-203)**
```css
[data-theme="dark"] .sidebar-new-chat-btn {
  background: #7c6ff7 !important;        /* ← var(--color-accent) (既に accent purple を使っている) */
  border-color: #7c6ff7 !important;
  color: #ffffff !important;             /* ← var(--color-accent-contrast) */
}
[data-theme="dark"] .sidebar-filter-input {
  background: #1e1e2e !important;        /* ← var(--color-bg) */
  color: #e8e8f0 !important;
  border-color: #3a3a52 !important;
}
[data-theme="dark"] .sidebar-thread-item.active {
  background: #313145 !important;        /* ← var(--color-surface-elevated) */
}
[data-theme="dark"] .sidebar-thread-delete-btn:hover {
  color: #e05252 !important;             /* ← var(--color-destructive) */
}
```

**抽出元: MessageArea app-class override (theme.css L209-252)**
```css
[data-theme="dark"] .chat-input-bar {
  background: #2a2a3e !important;        /* ← var(--color-surface) */
  border-top-color: #3a3a52 !important;  /* ← var(--color-border) */
}
[data-theme="dark"] .chat-textarea:focus {
  border-color: #7c6ff7 !important;      /* ← var(--color-accent) */
  outline: none;
}
[data-theme="dark"] .chat-send-btn {
  background: #7c6ff7 !important;        /* ← var(--color-accent) */
  color: #ffffff !important;             /* ← var(--color-accent-contrast) */
}
```

**追加方針 (RESEARCH.md §Pattern 1 L205-301 + §Pattern 4 L524-582):**
- **theme.css 冒頭** (L10 の color-scheme 定義の後) に `:root { /* primitive + semantic light */ }` と `[data-theme="dark"] { /* semantic dark override */ }` を追加。UI-SPEC §Token Layering の 2 層定義表に従う。
- **既存 L82-296 の hex** を機械的に `var(--...)` に置換。`!important` は据え置き (chatscope specificity 勝負のため)。RESEARCH.md §Pattern 2 L305-330 参照。
- **md-table** (L327-388) / **typing-dot** (L306-320) の hex も対象に含める (移行 4 対象外にだけ対応すると drift する)。
- **theme.css 末尾** に `/* Responsive */` セクションで `@media (max-width: 1024px)` / `@media (max-width: 767px)` を集約。コンポーネント CSS ファイル分離はしない (Open Question #4 決定)。
- `.cs-message--outgoing .cs-message__content-wrapper { max-width: 85% !important; }` は **tablet ブロック内に限定** (Pitfall 2 — incoming に絡ませない)。
- 新規 `.sidebar-drawer` / `.sidebar-backdrop` クラス (RESEARCH.md §Pattern 4 L548-561 + §Pattern 5 L588-618) を tablet/mobile ブロック内で定義。

**z-index 契約 (Pitfall 7 対応):**
- `ConfirmModal.tsx` L43 verified: `zIndex: 9999`
- drawer: `.sidebar-drawer { z-index: 50 }`、`.sidebar-backdrop { z-index: 49 }` で ConfirmModal (9999) より十分低い。安全。

---

### 6. `frontend/src/components/MenuScreen.tsx` (ダッシュボード再構築 + var() 移行)

**Analog:** 自身 L46-211 (既存 card grid) + 新規セクション構造

**抽出元: isDark 三項の削除 before (MenuScreen.tsx L17-27)**
```tsx
export function MenuScreen({ onNavigate, onOpenGems, onOpenDebate, onOpenCanvas }: MenuScreenProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';
  const screenBg = isDark ? '#1e1e2e' : '#f5f5f5';
  const cardBg = isDark ? '#2a2a3e' : '#fff';
  const textColor = isDark ? '#e0e0e0' : '#333';
  const cardBorder = isDark ? '#3a3a52' : '#ddd';
  const subtitleColor = isDark ? '#a0a0b8' : '#666';
  const mutedColor = isDark ? '#9090a8' : '#666666';
```
**→ after (RESEARCH.md §Example 1 L820-824):**
```tsx
export function MenuScreen(...) {
  // useCurrentTheme / isDark / 6 個の三項変数すべて削除
  // inline style 側で 'var(--color-bg)' / 'var(--color-surface)' / 'var(--color-text)' /
  //                 'var(--color-border)' / 'var(--color-text-muted)' を直接参照
```

**抽出元: 既存 hero タイトル (MenuScreen.tsx L61-85)**
```tsx
<h1 style={{
  fontFamily: "'Rajdhani', sans-serif",     // ← var(--font-family-display)
  fontSize: '2.8rem',                         // ← var(--font-display) (semi-shorthand)
  fontWeight: 700,
  marginBottom: '0.5rem',
  letterSpacing: '0.1em',
  background: 'linear-gradient(90deg, #a78bfa, #7c6ff7, #38bdf8)',
  //          ← var(--gradient-title) (theme 不変、UI-SPEC §Token 一覧)
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  backgroundClip: 'text',
}}>Orochi Chat</h1>
<p style={{
  fontSize: '1rem',
  color: subtitleColor,           // ← 'var(--color-text-muted)'
  marginBottom: error ? '1rem' : '2.5rem',
  textAlign: 'center',
}}>Choose an application to get started</p>   // ← 日本語化: 使いたいアプリを選んで始めましょう
```

**抽出元: 既存 error banner (MenuScreen.tsx L88-103)**
```tsx
<div role="alert" style={{
  background: 'rgba(224,82,82,0.1)',
  border: '1px solid #e05252',     // ← 'var(--color-destructive)'
  borderRadius: '8px',              // ← var(--radius-md) or --radius-lg
  padding: '12px 16px',
  color: '#e05252',                 // ← 'var(--color-destructive)'
  marginBottom: '2.5rem',
  width: '100%', maxWidth: '600px',
}}>{error}</div>                    // ← 日本語化 (UI-SPEC §Copywriting)
```

**抽出元: 既存 grid pattern (MenuScreen.tsx L106-114, L184-192)** → 3 セクション化
```tsx
<div style={{
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',  // ← 220px (UI-SPEC §Dashboard Grid)
  gap: '1rem',                    // ← 'var(--space-4)'
  width: '100%', maxWidth: '600px',
  marginBottom: '1rem',
}}>
```

**セクション構造 (UI-SPEC §Dashboard Visual Design + RESEARCH.md §Example 3 L898-931):**
```tsx
<section aria-labelledby="section-apps" style={{ marginTop: 'var(--space-8)' }}>
  <h2 id="section-apps" style={{ font: 'var(--font-heading)' }}>アプリケーション</h2>
  <div className="menu-card-grid">{/* FeatureCard array */}</div>
</section>

<section aria-labelledby="section-recent">
  <h2 id="section-recent">最近のスレッド</h2>
  {/* RecentThreadCard × 5 */}
</section>

<section aria-labelledby="section-other">
  <h2 id="section-other">その他</h2>
  <p style={{ color: 'var(--color-text-muted)' }}>アプリが足りない場合は管理者にご相談ください。</p>
</section>
```

**最近スレッドのデータ取得 (RESEARCH.md §Pitfall 3 L734-747):**
- `listThreads()` は `frontend/src/api/client.ts` L72 に既存 — `(appId?, gemId?) =>` の signature。全アプリ横断かは backend 実装依存だが planner が Wave 0 で `app/api/routes/threads.py` を 1 回確認 (A2)。
- MenuScreen 側で必ず client-side sort:
```tsx
const recentThreads = useMemo(
  () => [...allThreads]
    .sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''))
    .slice(0, 5),
  [allThreads]
);
```

---

### 7. `frontend/src/components/MessageArea.tsx` (InputBar 分離 + var() 移行)

**Analog:** 自身 L383-485 (既存 chat-input-bar ブロック) → InputBar.tsx へ移設

**残す側の抽出元: thinking 状態の inline indicator (MessageArea.tsx L321-380)**
```tsx
{isThinking && (
  <Message model={{ direction: 'incoming', position: 'single', type: 'custom' }}>
    <Message.CustomContent>
      <div style={{ display: 'flex', gap: '5px', alignItems: 'center', padding: '2px 0' }}>
        <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
        {elapsed > 0 && (
          <span style={{
            fontSize: '0.75rem',
            color: isDark ? '#9090a8' : '#888',   // ← 'var(--color-text-muted)'
            marginLeft: 8,
            fontVariantNumeric: 'tabular-nums',
          }}>{elapsed}s</span>
        )}
        {onCancel && (
          <button onClick={onCancel} title="応答をキャンセル"
            style={{
              background: 'none',
              border: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,  // ← 1 枚化
              borderRadius: '4px',                // ← 'var(--radius-sm)'
              cursor: 'pointer',
              fontSize: '0.72rem',
              color: isDark ? '#9090a8' : '#888', // ← 'var(--color-text-muted)'
              padding: '1px 6px', marginLeft: 8,
            }}>
            ✕ キャンセル
          </button>
        )}
      </div>
```

**残す側の抽出元: resend checkbox (MessageArea.tsx L244-254, L304-314)**
```tsx
{enableResend && (
  <label style={{
    display: 'flex', alignItems: 'center', gap: '3px',
    fontSize: '0.72rem',
    color: isDark ? '#9090a8' : '#888',     // ← 'var(--color-text-muted)'
    cursor: 'pointer', marginLeft: 'auto',
  }}>
    <input type="checkbox" checked={isIncluded}
      onChange={() => toggleMsgInclusion(index)}
      style={{ margin: 0, cursor: 'pointer', accentColor: '#0366d6' }}
      // ← accentColor: 'var(--color-accent)'
    />
    送信に含める
  </label>
)}
```

**InputBar 差し込み (RESEARCH.md L494-510):**
```tsx
{pendingQuestion ? (
  <div className="chat-input-bar" style={{ padding: '0.75rem', background: 'var(--color-surface)', borderTop: '1px solid var(--color-border)' }}>
    <QuestionPanel questions={pendingQuestion.questions} onSubmit={onQuestionSubmit!} />
  </div>
) : (
  <InputBar
    value={inputValue} onChange={setInputValue}
    onSend={handleSendWrapped}    // contextMessages 組み立ては MessageArea に残す
    onCancel={onCancel}
    onAskMe={handleAskMeWrapped}  // AUQ suffix は MessageArea で付与
    isThinking={isThinking} disabled={disabled} placeholder={placeholder}
    copyAllSlot={messages.length > 0 ? <CopyAllButton messages={messages} /> : undefined}
    // toolbarSlot / previewSlot は Phase 35 では未指定 (Phase 36 で差し込み)
  />
)}
```

**既存 critical 挙動 (ADR-0043 — 壊さないこと):**
- `CopyAllButton` L76-79 の defense-in-depth (`typeof === 'string'` + `JSON.stringify` fallback) は保持。
- `MarkdownMessage` の string content 制約 (L299) は保持。
- `MessageList` は `<div className="cs-chat-container">` の中で L205-382 既存構造で維持。

---

### 8. `frontend/src/components/ThreadSidebar.tsx` (drawer 化 + var() 移行)

**Analog:** 自身 L148-498 (既存 collapse / filter / date group / bulk select)

**抽出元: 既存 collapse 時 return 分岐 (ThreadSidebar.tsx L148-170)**
```tsx
if (collapsed) {
  return (
    <Sidebar position="left" style={{ width: `${width}px`, ... }}>
      <div className="sidebar-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '0.5rem 0', height: '100%' }}>
        <button onClick={onToggleCollapse} title="Expand sidebar"
          className="sidebar-collapse-btn"
          style={{ background: 'none', border: 'none', cursor: 'pointer',
            fontSize: '1.1rem', color: '#555',  // ← 'var(--color-text-muted)'
            padding: '4px',
          }}>▶</button>
      </div>
    </Sidebar>
  );
}
```

**抽出元: New Chat ボタン (ThreadSidebar.tsx L178-194)**
```tsx
<button onClick={onNewChat} className="sidebar-new-chat-btn"
  style={{
    flex: 1, padding: '0.5rem',
    cursor: 'pointer',
    borderRadius: '6px',                  // ← 'var(--radius-md)'
    border: '1px solid #ddd',             // ← '1px solid var(--color-border)'
    background: '#0366d6',                // ← 'var(--color-accent)' (UI-SPEC Accent reserved-for #2)
    color: '#fff',                        // ← 'var(--color-accent-contrast)'
    fontWeight: 'bold', fontSize: '0.9rem',
  }}>+ New Chat</button>                  // ← 日本語化: + 新しいチャット
```

**抽出元: bulk delete ボタン (ThreadSidebar.tsx L249-263)**
```tsx
<button onClick={() => setBulkDeleteConfirm(true)}
  style={{
    background: '#e05252',            // ← 'var(--color-destructive)'
    border: 'none',
    borderRadius: '4px',              // ← 'var(--radius-sm)'
    cursor: 'pointer',
    fontSize: '0.75rem',
    color: '#fff', padding: '2px 8px', fontWeight: 600,
  }}>{selectedIds.size}件削除</button>
```

**抽出元: active thread item (ThreadSidebar.tsx L360-370)**
```tsx
<div className={`sidebar-thread-item${activeThreadId === thread.thread_id ? ' active' : ''}`}
  style={{
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0.4rem 0.5rem',
    borderRadius: '4px',
    cursor: 'pointer',
    background: activeThreadId === thread.thread_id ? '#e8f0fe' : 'transparent',
    //          ← 'var(--color-accent-subtle)' (UI-SPEC Semantic token)
    fontWeight: activeThreadId === thread.thread_id ? 'bold' : 'normal',
  }}>
```

**drawer 化パターン (RESEARCH.md §Pattern 5 L588-618):**
```tsx
const [drawerOpen, setDrawerOpen] = useState(false);

useEffect(() => {
  if (!drawerOpen) return;
  const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawerOpen(false); };
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
}, [drawerOpen]);

return (
  <>
    {drawerOpen && <div className="sidebar-backdrop" onClick={() => setDrawerOpen(false)} />}
    <aside className={`sidebar-drawer ${drawerOpen ? 'open' : ''}`}
      role={drawerOpen ? 'dialog' : undefined}
      aria-modal={drawerOpen ? 'true' : undefined}
      aria-label={drawerOpen ? 'スレッド一覧' : undefined}>
      {/* 既存 Sidebar 中身 */}
    </aside>
  </>
);
```

**getDateGroup 移行 (item 3 参照):** L61-86 を丸ごと削除し `import { getDateGroup, groupThreads, groupOrder, type DateGroup } from '../utils/threadGroups'`。L88 の `groupThreads(filtered)` 呼び出しは名前一致で import 後もそのまま動く。

**ConfirmModal の `isDark` prop (ThreadSidebar.tsx L479, L492):**
- 既存 `isDark={isDark}` は保持してよい（ConfirmModal 自体は Phase 35 scope 外、UI-SPEC L350）。ただし `isDark` 変数生成 (L40) は削除対象 (UX-04-6)。`isDark={theme === 'dark'}` のインライン化を planner が選択するか、`ConfirmModal.tsx` 側で `useCurrentTheme()` に切替するかは判断。

---

### 9. `frontend/src/components/Header.tsx` (hamburger 追加 + var() 移行)

**Analog:** 自身 L69-207 (既存 flex 横並び)

**抽出元: isDark 三項 before (Header.tsx L65-67)**
```tsx
const isDark = theme === 'dark';
const headerBg = isDark ? '#1e1e2e' : '#24292e';      // ← 'var(--color-header-bg)'
const headerBorder = isDark ? '#3a3a52' : '#1b1f23';  // ← 'var(--color-border)'
```

**抽出元: header 本体 (Header.tsx L70-80)**
```tsx
<header style={{
  display: 'flex', alignItems: 'center',
  padding: '0 1rem',
  height: '48px',                       // ← UI-SPEC §Spacing で 48px 明示
  background: headerBg,                 // ← 'var(--color-header-bg)'
  color: '#fff',                        // ← 'var(--color-header-text)'
  gap: '1rem',                          // ← 'var(--space-4)'
  flexShrink: 0,
  borderBottom: `1px solid ${headerBorder}`,  // ← '1px solid var(--color-border)'
}}>
```

**抽出元: Orochi Chat タイトル gradient (Header.tsx L98-107)**
```tsx
<span style={{
  fontFamily: "'Rajdhani', sans-serif",
  fontWeight: 700,
  fontSize: '1.25rem',
  letterSpacing: '0.08em',
  background: 'linear-gradient(90deg, #a78bfa, #7c6ff7, #38bdf8)',
  //          ← 'var(--gradient-title)' (theme 不変、token 化後も同じ見た目)
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  backgroundClip: 'text',
}}>Orochi Chat</span>
```

**抽出元: Back to menu / Logout / Theme toggle ボタン (Header.tsx L81-96, L159-193)**
```tsx
// Back to menu
<button style={{
  padding: '0.25rem 0.75rem',
  cursor: 'pointer',
  borderRadius: '4px',                  // ← 'var(--radius-sm)'
  border: '1px solid #555',             // ← '1px solid var(--color-border)'
  background: 'transparent',
  color: '#ccc',                        // ← 'var(--color-header-text)' + opacity、or muted
  fontSize: '0.85rem',
  flexShrink: 0,
}}>&lsaquo; Menu</button>               // ← 日本語化: ‹ メニュー

// Logout ボタン L159-174: 同じ style
// Theme toggle L176-193: 同じ style
```

**hamburger menu 新規 (RESEARCH.md §Pattern 6 L630-651):**
```tsx
<details className="header-hamburger" style={{ display: 'none' /* @media で override */ }}>
  <summary aria-label="メニューを開く" style={{ listStyle: 'none', cursor: 'pointer', padding: '4px 8px' }}>
    ☰
  </summary>
  <div role="menu" style={{
    position: 'absolute', right: 0, top: '48px',
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-2)',
    minWidth: '200px', zIndex: 40,
  }}>
    {/* Model select, Logout, Theme toggle を縦に並べる */}
  </div>
</details>
```

**Pitfall 5 注意:** `<summary>` の中に `<button>` を入れない (Safari クリック競合)。`<summary>` 自体を clickable にし `list-style: none` で ▸ 消す。

**@media 連動:** `.header-hamburger` は default `display: none`、`@media (max-width: 767px)` で `display: inline-flex !important`。Model select / Logout / username は mobile で非表示 (UI-SPEC §Responsive)。tablet では `.header-model-label` / `.header-user-login` のみ非表示 (RESEARCH.md §Pattern 4 L533-541)。

---

## Shared Patterns

### Theme 切替 — `data-theme="dark"` 属性切替 (D-01 locked)

**Source:** `frontend/src/contexts/ThemeContext.ts` + `frontend/src/hooks/useTheme.ts` (既存、Phase 35 で触らない)

**Apply to:** 全 4 コンポーネント。ただし **component 側で `theme === 'dark'` を読まない**。CSS 変数経由で解決する。

```tsx
// BEFORE (全コンポーネント共通パターン)
const theme = useCurrentTheme();
const isDark = theme === 'dark';
const bg = isDark ? '#1e1e2e' : '#f5f5f5';
<div style={{ background: bg }}>

// AFTER
// useCurrentTheme / isDark 削除
<div style={{ background: 'var(--color-bg)' }}>
```

### chatscope `!important` override の変数駆動置換 (RESEARCH.md §Pattern 2)

**Source:** `frontend/src/theme.css` L82-252 の全 `[data-theme="dark"] .cs-* / .sidebar-* / .chat-* / .auth-*` ブロック

**Apply to:** theme.css 全 398 行の hex 値 (primitive 宣言行を除く)

**移行ルール:**
- `!important` は外さない (chatscope specificity 勝負)
- `background: #1e1e2e !important;` → `background: var(--color-bg) !important;` のように値のみ置換
- `:root { --x: ... !important; }` の custom property 側 `!important` と、実 property 側 `!important` は独立 ([CITED: stefanjudis.com])

### ConfirmModal (Phase 35 scope 外、interaction のみ)

**Source:** `frontend/src/components/ConfirmModal.tsx` L31-96

**Apply to:** Logout (Header.tsx L195-205)、Thread 削除 (ThreadSidebar.tsx L474-485)、Bulk 削除 (ThreadSidebar.tsx L487-495)

**既存 z-index:** `9999` (L43) — drawer backdrop (49) より確実に高い。Pitfall 7 不発。

**注意:** ConfirmModal は UI-SPEC §Component Migration Scope で「触らない」。`isDark` prop はそのまま渡してよい (ConfirmModal 内部が `isDark ?` を使っているが Phase 35 対象外)。

### Focus ring — 新規ボタン共通 (UI-SPEC §Visual Accessibility Baseline)

**Apply to:** Phase 35 で新規追加する button 群 — FeatureCard (拡張)、RecentThreadCard、drawer hamburger、InputBar の Send/AskMe/Cancel

```css
/* theme.css の新規ユーティリティ */
.menu-card:focus-visible,
.recent-thread-card:focus-visible,
.header-hamburger summary:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

### `listThreads` / `getApps` の呼び出し (既存 API client)

**Source:** `frontend/src/api/client.ts` L72 (`listThreads`), L150 (`getApps`)

**Apply to:** MenuScreen (最近スレッド取得 + apps 取得、既存踏襲)

---

## No Analog Found

該当なし — Phase 35 は完全に既存コード内のリファクタ + 切り出し phase で、全新規ファイルに 1:1 の移行元 / 拡張元がある。

---

## Pitfall Line References (RESEARCH.md §Common Pitfalls)

planner がタスクに埋め込む際の参照ポイント。RESEARCH.md 該当行番号を併記:

| # | Pitfall | RESEARCH.md 行 | 影響ファイル |
|---|---------|----------------|--------------|
| 1 | theme.css と inline style の片側だけ変数化 | L707-719 | 全 4 tsx + theme.css |
| 2 | `.cs-message--incoming` も `max-width: 85%` にしてしまう | L721-731 | theme.css @media tablet |
| 3 | `listThreads()` が updated_at desc でない | L734-747 | MenuScreen.tsx |
| 4 | AUQ suffix が InputBar に漏れる | L749-754 | InputBar.tsx / MessageArea.tsx |
| 5 | `<details><summary><button>` クリック競合 | L756-767 | Header.tsx |
| 6 | `var(--x)` 未定義で Safari 真っ黒/真っ白 | L769-779 | theme.css primary surface |
| 7 | drawer backdrop z-index が ConfirmModal より高い | L781-790 | theme.css (.sidebar-backdrop: 49) / ConfirmModal.tsx (verified 9999) |
| 8 | InputBar に `excludedIndices` / `elapsed` を移動 | L793-798 | MessageArea.tsx / InputBar.tsx |

---

## Metadata

**Analog search scope:**
- `frontend/src/components/*.tsx` (既存のコンポーネント内類似構造)
- `frontend/src/theme.css` (全行)
- `frontend/src/utils/*.ts` (純粋関数 utils のスタイル踏襲)
- `scripts/*.sh` (bash harness 構成)
- `frontend/src/types.ts` (ThreadInfo 型 verify — A1 部分解消)
- `frontend/src/components/ConfirmModal.tsx` (z-index 9999 verify — A3 解消)
- `frontend/src/api/client.ts` (`listThreads` / `getApps` signature verify)

**Files scanned:** 9 ファイル (全て Read で読了、重複 Read なし)

**Assumption 解消状況:**
- **A1 (ThreadInfo に `app_id` / `gem_id`):** `app_id?: string` は存在、`gem_id` フィールドは無し。RecentThreadCard routing は app_id 中心でOK。
- **A3 (ConfirmModal z-index):** `9999` (ConfirmModal.tsx L43) verified、drawer backdrop 49 で安全。
- **A2 / A5 / A6 / A7:** 未解消 — planner の Wave 0 タスクで 5-15 分 verify を残す。

**Pattern extraction date:** 2026-04-23
