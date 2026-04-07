---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/chat/APP.md
  - app/api/models.py
  - app/api/routes/apps.py
  - frontend/src/types.ts
  - frontend/src/App.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "メニューから Chat を選択すると ChatApp がレンダリングされ、GemSelector は表示されない"
    - "メニューから SuperChat を選択すると SuperChatApp がレンダリングされ、GemSelector が表示される"
    - "GET /api/apps が Chat に type='chat'、SuperChat に type='superchat' を返す"
  artifacts:
    - path: "apps/chat/APP.md"
      provides: "type: chat フロントマター"
      contains: "type: chat"
    - path: "app/api/models.py"
      provides: "AppInfo.type フィールド"
      contains: "type: str"
    - path: "frontend/src/App.tsx"
      provides: "type による chat/superchat ルーティング分岐"
      contains: "chat"
  key_links:
    - from: "apps/chat/APP.md"
      to: "app/api/routes/apps.py"
      via: "frontmatter type field read"
      pattern: "post\\.metadata\\.get.*type"
    - from: "frontend/src/App.tsx"
      to: "frontend/src/components/ChatApp.tsx"
      via: "handleNavigate type check"
      pattern: "type.*chat"
---

<objective>
ChatApp ルーティング修正: APP.md の type フィールドで Chat と SuperChat のコンポーネントを分岐する。

Purpose: メニューから Chat を選択した際に SuperChatApp ではなく ChatApp がレンダリングされるようにする。現状は全アプリが SuperChatApp にルーティングされ、Chat でも GemSelector が表示されてしまうバグを修正する。
Output: type フィールドによるルーティング分岐が機能し、Chat は ChatApp、SuperChat は SuperChatApp を使う。
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@apps/chat/APP.md
@apps/superchat/APP.md
@app/api/models.py
@app/api/routes/apps.py
@frontend/src/types.ts
@frontend/src/App.tsx
@frontend/src/components/ChatApp.tsx
@frontend/src/components/SuperChatApp.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — APP.md に type フィールド追加、AppInfo モデル拡張、apps.py で読み取り</name>
  <files>apps/chat/APP.md, app/api/models.py, app/api/routes/apps.py</files>
  <action>
1. `apps/chat/APP.md` のフロントマターに `type: chat` を追加する（agents の後に配置）。
2. `apps/superchat/APP.md` はデフォルト値 superchat で動作するため変更不要。
3. `app/api/models.py` の `AppInfo` クラスに `type: str = "superchat"` フィールドを追加する。デフォルト値 `"superchat"` により、type が未指定の既存 APP.md は SuperChat として扱われる。
4. `app/api/routes/apps.py` の `list_apps` 関数で `post.metadata.get("type", "superchat")` を読み取り、`AppInfo(...)` コンストラクタに `type=app_type` を渡す。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && python -c "
import frontmatter
post = frontmatter.load('apps/chat/APP.md')
assert post.metadata.get('type') == 'chat', f'Expected chat, got {post.metadata.get(\"type\")}'
print('APP.md type=chat OK')

from app.api.models import AppInfo
info = AppInfo(slug='test', name='Test', description='', icon='', agents=[], type='chat')
assert info.type == 'chat'
info2 = AppInfo(slug='test', name='Test', description='', icon='', agents=[])
assert info2.type == 'superchat', f'Default should be superchat, got {info2.type}'
print('AppInfo model OK')
"
    </automated>
  </verify>
  <done>APP.md に type: chat が設定され、AppInfo モデルが type フィールドを持ち、apps.py が frontmatter から type を読み取って返す</done>
</task>

<task type="auto">
  <name>Task 2: Frontend — AppDefinition に type 追加、App.tsx で chat/superchat ルーティング分岐</name>
  <files>frontend/src/types.ts, frontend/src/App.tsx</files>
  <action>
1. `frontend/src/types.ts` の `AppDefinition` インターフェースに `type?: string;` フィールドを追加する（agents の後に配置）。

2. `frontend/src/App.tsx` を以下のように修正:
   a. Screen 型に `'chat'` を追加: `type Screen = 'menu' | 'chat' | 'superchat' | 'gems' | 'gemchat' | 'debate' | 'canvas' | 'canvaschat';`
   b. コメント行（line 4）を更新: `8-screen navigation: menu | chat | superchat | gems | gemchat | debate | canvas | canvaschat`
   c. `import { ChatApp } from './components/ChatApp';` を追加
   d. `handleNavigate` 関数を修正:
      ```typescript
      const handleNavigate = (app: AppDefinition) => {
        setActiveApp(app);
        setCurrentScreen(app.type === 'chat' ? 'chat' : 'superchat');
      };
      ```
   e. `{currentScreen === 'superchat' && (` ブロックの直前に、chat スクリーンのレンダリングブロックを追加:
      ```tsx
      {currentScreen === 'chat' && (
        <>
          <Header
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
            theme={theme}
            onToggleTheme={toggleTheme}
            onBackToMenu={handleBackToMenu}
            appName={activeApp?.name}
          />
          <ChatApp selectedModel={selectedModel} />
        </>
      )}
      ```
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>Chat アプリ選択時に ChatApp コンポーネントがレンダリングされ、SuperChat 選択時は従来通り SuperChatApp がレンダリングされる。TypeScript コンパイルエラーなし。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| API -> Frontend | type フィールドは API が返す値をそのまま使用 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-quick-01 | Tampering | APP.md type field | accept | type フィールドは表示ルーティングのみに使用、セキュリティ境界に影響しない。不正な type 値は superchat にフォールバック。 |
</threat_model>

<verification>
1. `GET /api/apps` が Chat に `type: "chat"`、SuperChat に `type: "superchat"` を返すこと
2. メニューから Chat 選択 → ChatApp がレンダリングされ GemSelector が表示されないこと
3. メニューから SuperChat 選択 → SuperChatApp がレンダリングされ GemSelector が表示されること
</verification>

<success_criteria>
- Chat アプリが ChatApp コンポーネントで動作し、GemSelector が表示されない
- SuperChat アプリが SuperChatApp コンポーネントで動作し、GemSelector が表示される
- TypeScript コンパイルエラーなし
- 既存の SuperChat/Gems/Debate/Canvas 画面に影響なし
</success_criteria>

<output>
After completion, create `.planning/quick/260407-vqs-chatapp-app-md-type-chat-superchat/260407-vqs-SUMMARY.md`
</output>
