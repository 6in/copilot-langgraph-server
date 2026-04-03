---
phase: quick
plan: 260403-dyf
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/api/client.ts
  - frontend/src/components/MenuScreen.tsx
  - frontend/src/components/Header.tsx
  - frontend/src/App.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "After login, user sees a menu screen with app title and a Chat feature card"
    - "Clicking the Chat card navigates to the existing ChatApp view"
    - "From ChatApp, user can navigate back to the menu screen via a button in the Header"
    - "API calls work with and without VITE_BASE_URL prefix (default empty string)"
  artifacts:
    - path: "frontend/src/components/MenuScreen.tsx"
      provides: "Menu/home screen with feature cards"
      min_lines: 30
    - path: "frontend/src/api/client.ts"
      provides: "BASE_URL prefix on all API paths"
      contains: "VITE_BASE_URL"
    - path: "frontend/src/App.tsx"
      provides: "Screen routing state: menu | chat"
      contains: "currentScreen"
  key_links:
    - from: "frontend/src/App.tsx"
      to: "frontend/src/components/MenuScreen.tsx"
      via: "currentScreen state toggle"
      pattern: "setCurrentScreen"
    - from: "frontend/src/components/Header.tsx"
      to: "frontend/src/App.tsx"
      via: "onBackToMenu callback prop"
      pattern: "onBackToMenu"
    - from: "frontend/src/api/client.ts"
      to: "import.meta.env.VITE_BASE_URL"
      via: "BASE_URL constant prepended to all fetch paths"
      pattern: "BASE_URL"
---

<objective>
Add a menu/home screen as the landing page after authentication, and make the API client's URL prefix configurable via VITE_BASE_URL.

Purpose: Users currently land directly in ChatApp after login. A menu screen provides a hub for future features (Gem, Canvas, etc.) and the URL prefix enables deployment behind a reverse proxy with a path prefix.
Output: MenuScreen component, updated App.tsx routing, Header back button, configurable API base URL.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/App.tsx
@frontend/src/components/ChatApp.tsx
@frontend/src/components/Header.tsx
@frontend/src/api/client.ts
@frontend/src/hooks/useAuth.ts

<interfaces>
From frontend/src/App.tsx:
```typescript
// Current auth gate: isAuthenticated ? ChatApp : AuthPanel
// Will add: currentScreen state ('menu' | 'chat')
```

From frontend/src/components/Header.tsx:
```typescript
interface HeaderProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  // Will add: onBackToMenu?: () => void
}
```

From frontend/src/api/client.ts:
```typescript
// Current: apiFetch<T>(path: string, init?: RequestInit)
// All paths hardcoded as '/api/...'
// streamJob uses new EventSource('/api/...')
// deleteThread uses raw fetch('/api/...')
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add VITE_BASE_URL support to API client</name>
  <files>frontend/src/api/client.ts</files>
  <action>
Add a BASE_URL constant at the top of client.ts:

```typescript
const BASE_URL = import.meta.env.VITE_BASE_URL ?? '';
```

Update apiFetch to prepend BASE_URL to path:
```typescript
const resp = await fetch(`${BASE_URL}${path}`, { credentials: 'include', ...init });
```

Update streamJob to prepend BASE_URL:
```typescript
export const streamJob = (jobId: string): EventSource =>
  new EventSource(`${BASE_URL}/api/chat/${encodeURIComponent(jobId)}/stream`);
```

Update deleteThread raw fetch to prepend BASE_URL:
```typescript
const resp = await fetch(`${BASE_URL}/api/threads/${encodeURIComponent(threadId)}`, {
```

All other functions go through apiFetch so they get the prefix automatically. No other changes needed.

Default is empty string so current behavior is preserved with no env var set.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend && grep -c "BASE_URL" src/api/client.ts | grep -q "^[4-9]" && echo "PASS: BASE_URL used in multiple places" || echo "FAIL"</automated>
  </verify>
  <done>BASE_URL constant defined from VITE_BASE_URL, prepended in apiFetch, streamJob, and deleteThread. Empty string default preserves current behavior.</done>
</task>

<task type="auto">
  <name>Task 2: Create MenuScreen component and wire screen navigation in App.tsx + Header</name>
  <files>frontend/src/components/MenuScreen.tsx, frontend/src/App.tsx, frontend/src/components/Header.tsx</files>
  <action>
**MenuScreen.tsx** - Create new component:
- Accept props: `{ onNavigate: (screen: string) => void }`
- Render app title "Copilot Chat" prominently centered
- Render a feature card grid (CSS grid, responsive)
- First card: "Chat" with a chat bubble icon (use unicode or simple SVG), brief description "AI-powered chat with GitHub Copilot", onClick calls `onNavigate('chat')`
- Style: cards with border, border-radius 12px, padding 1.5rem, hover shadow effect, cursor pointer
- Use ThemeContext to read current theme and apply appropriate colors (dark: #1e1e2e bg, #2a2a3e card bg, #e0e0e0 text; light: #f5f5f5 bg, #fff card bg, #333 text)
- Import useContext and ThemeContext from '../contexts/ThemeContext'
- Card grid: max-width 600px centered, gap 1rem, grid-template-columns repeat(auto-fill, minmax(180px, 1fr))

**App.tsx** - Add screen routing:
- Add state: `const [currentScreen, setCurrentScreen] = useState<'menu' | 'chat'>('menu');`
- In the authenticated branch, conditionally render:
  - If currentScreen === 'menu': render `<Header ... />` (without back button) + `<MenuScreen onNavigate={(s) => setCurrentScreen(s as 'menu' | 'chat')} />`
  - If currentScreen === 'chat': render `<Header ... onBackToMenu={() => setCurrentScreen('menu')} />` + `<ChatApp ... />`
- Keep the outer flex column div for both cases
- Import MenuScreen

**Header.tsx** - Add optional back-to-menu button:
- Add optional prop `onBackToMenu?: () => void` to HeaderProps
- When onBackToMenu is provided, render a back arrow button (unicode arrow "< Menu") as the first element before the "Copilot Chat" title span
- Style: same transparent button style as Logout button, positioned at start of header
- When onBackToMenu is NOT provided (menu screen), do not render the button
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend && npx tsc --noEmit 2>&1 | tail -5</automated>
  </verify>
  <done>MenuScreen renders with Chat feature card. App.tsx routes between menu and chat via useState. Header shows back button only in chat view. TypeScript compiles without errors.</done>
</task>

</tasks>

<verification>
1. `cd frontend && npx tsc --noEmit` — no type errors
2. `cd frontend && npx vite build` — production build succeeds
3. Manual: after login, menu screen shows. Click Chat -> ChatApp appears with back button in header. Click back -> menu screen returns.
</verification>

<success_criteria>
- MenuScreen component exists and renders feature cards
- App.tsx gates between menu and chat screens after auth
- Header shows back-to-menu button only in chat view
- API client prepends VITE_BASE_URL (default empty) to all fetch calls
- TypeScript compiles, Vite builds successfully
</success_criteria>

<output>
After completion, create `.planning/quick/260403-dyf-add-menu-screen-and-configurable-url-pre/260403-dyf-SUMMARY.md`
</output>
