# Feature Landscape

**Domain:** Personal LLM Chat Web App (GitHub Copilot via LangGraph)
**Researched:** 2026-03-31
**Overall confidence:** HIGH

---

## Context

This is a single-user, locally-run chat interface over GitHub Copilot using a custom
`ChatCopilot` (`BaseChatModel`) provider. The backend is Python (FastAPI + LangGraph).
The frontend is a browser-based chat UI. No multi-user, no streaming (Copilot SDK
does not support it in v1), no tool calling in v1.

Scope anchor: a developer's personal daily-driver tool, not a product for others.
The comparison baseline is Open WebUI, LibreChat, and TypingMind — but stripped to
the minimal viable surface that feels complete, not broken.

---

## Table Stakes

Features where absence makes the tool feel broken or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Message history display | Without it there is no "chat" — just a single-shot box | Low | Chronological scroll, user and assistant bubbles clearly distinguished |
| Multi-turn thread (context accumulation) | Each message must carry prior history to the model | Medium | LangGraph `messages` state; must persist within a session |
| Send / receive flow | Type → submit → wait → display response | Low | Disable input while awaiting response to prevent double-sends |
| Loading / thinking indicator | No feedback during LLM call (which takes 2-10 s) breaks perceived reliability | Low | Spinner or animated dots on the assistant bubble |
| New chat button | Without it, context never resets; old irrelevant history poisons new topics | Low | Clears in-memory thread, starts fresh LangGraph state |
| Markdown rendering in assistant bubbles | Code blocks, bold, lists from LLM output are unreadable as raw text | Medium | `react-markdown` + `remark-gfm` + `react-syntax-highlighter`; user bubbles stay plain text |
| Error display inline | Silent failure after a 10 s wait is deeply frustrating | Low | Inline error message in the conversation, not just a console log |
| Device Flow auth trigger + status | The whole tool is gated on a valid Copilot token | Medium | On first launch (or token missing), surface the verification URL + code; show "authenticated as X" in UI header |
| Keyboard send (Enter) | Every chat tool works this way; mouse-only is friction | Low | Shift+Enter for newline |
| Auto-scroll to latest message | Without it the user must manually scroll after every response | Low | Scroll to bottom on new message append |

**Dependency chain:**

```
Device Flow auth
  └─ ChatCopilot client initialised
       └─ LangGraph graph can invoke
            └─ Send/receive flow works
                 └─ Multi-turn thread
                      └─ Message history display
```

---

## Differentiators

Features that make this more useful than typing into the raw Copilot CLI.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Model selector dropdown | Copilot exposes GPT-4.1, Claude Sonnet 4.x, Gemini 2.5 Pro, and more; switching per-conversation is genuinely useful | Low | Dropdown in the header; selected model stored in component state and passed to `ChatCopilot(model=...)` on each invocation |
| Session sidebar (conversation list) | Named chat sessions let you return to a prior context without losing it | High | Requires persistence (SQLite or JSON file); worth deferring to v2 unless persistence is trivial |
| Token expiry detection + re-auth prompt | Copilot `ghu_` tokens expire; silent 401 errors cause confusion | Medium | Detect auth error from backend, surface "Session expired — re-authenticate" button that triggers Device Flow again |
| Conversation title auto-generation | Sidebar sessions need names; asking the model to summarize in 5 words is low cost | Medium | Requires sidebar to be built first; low priority without session persistence |
| Copy response button | Code-heavy responses are almost always copied somewhere; one click > highlight+copy | Low | Per-message copy icon; clipboard API |
| Syntax-highlighted code blocks with language label | Code is the primary output for a developer tool; raw monospace is not enough | Low | Handled by `react-syntax-highlighter` with Prism; add language label from fenced-code info string |

**For v1, ship:** model selector, inline error with re-auth trigger, copy button, syntax-highlighted code blocks.

**Defer:** session sidebar, auto-generated titles (depend on persistence layer not in v1 scope).

---

## Anti-Features

Things to deliberately NOT build in v1. These are traps, not features.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| User accounts / login screen | Single-user personal tool; a login form adds friction and complexity with zero security benefit when the app is localhost-only | Trust localhost; token lives in `~/.copilot_sdk/token.enc` |
| Multi-user token store (Redis) | Explicitly out of scope in PROJECT.md; premature for a solo tool | Design the auth manager so it can be swapped later (already done via `CopilotAuthManager`) |
| Streaming responses | Copilot SDK does not support it; building fake streaming (progressive reveal) misleads users about what the system is doing | Show a loading indicator; display full response when ready |
| Conversation search | Requires a persistence + indexing layer; not needed until there are >20 sessions | Defer until session list exists |
| Prompt templates / system prompt editor | Adds UI surface and cognitive overhead for a tool you control; edit the server config directly | Hard-code sensible system prompt in the LangGraph graph; expose as env var at most |
| File upload / image input | Copilot SDK `send_and_wait` takes a prompt string; multimodal input requires different API surface | Not blocked, just not in scope; add when SDK exposes it |
| Export conversation (PDF / Markdown) | Nice but zero-session-value: you can select-all and copy | Copy-message button covers 90% of the need |
| Dark/light mode toggle | Personal tool; set it once via OS preference and `prefers-color-scheme` media query | Respect OS theme automatically; no toggle needed |
| Rate limit display / token usage counter | Copilot SDK response object does not expose token counts in Technical Preview | Omit; add when the SDK surfaces usage data |
| Regenerate / edit message branching | Increases state complexity significantly (message tree vs. message list) | Simple linear history is fine for a personal tool |

---

## Feature Dependencies

```
auth (Device Flow + token storage)
  └─ chat backend (FastAPI + LangGraph + ChatCopilot)
       ├─ send/receive flow
       │    ├─ loading indicator
       │    ├─ inline error display
       │    │    └─ re-auth trigger (token expiry handling)
       │    └─ auto-scroll
       ├─ multi-turn thread (LangGraph state)
       │    └─ message history display
       │         └─ markdown rendering
       │              └─ code block highlighting
       │              └─ copy button
       └─ model selector (per-invocation model param)

new chat button
  └─ resets LangGraph state + clears message list
```

Features with no upstream dependencies (can be built in parallel or first):
- keyboard send shortcut
- auto-scroll
- loading indicator
- markdown/syntax rendering (pure frontend, mockable)

---

## MVP Recommendation

**Phase 1 — Backend core:** `ChatCopilot` provider + Device Flow auth + LangGraph graph with
thread state. No UI. Validate that a conversation with context actually works end-to-end
via a Python REPL or CLI script.

**Phase 2 — Minimal UI:** FastAPI endpoint + React chat UI with:
- Message history display (user + assistant bubbles)
- Send / receive flow with loading indicator
- Markdown + syntax highlighting in assistant bubbles
- Keyboard send (Enter / Shift+Enter)
- Auto-scroll
- Inline error display
- New chat button
- Auth status in header with Device Flow trigger

This is already a complete, non-broken tool at Phase 2.

**Phase 3 — Quality of life:** Add model selector dropdown, token-expiry re-auth prompt,
and copy-message button. These are the differentiators that make it better than a CLI
but require the Phase 2 skeleton to be stable first.

**Deliberately defer to v2 or later:**
- Session persistence (SQLite)
- Conversation sidebar + session list
- Auto-generated session titles
- Any feature that requires the Copilot SDK to expose streaming or token usage

---

## Notes on Copilot-Specific Constraints

1. **No streaming.** The SDK's `send_and_wait` is blocking and returns the full response.
   The UI must show a spinner for the entire round-trip (typically 2-15 seconds for long
   responses). Do not try to fake token-by-token streaming.

2. **Model list is dynamic.** Several Copilot models are marked "preview" or have
   deprecation dates (e.g. some GPT-5.1 variants deprecated 2026-04-01). The model
   selector should either hard-code a curated list (gpt-4.1, claude-sonnet-4-5,
   gemini-2.5-pro) or fetch from a config file, not from training-time assumptions.
   HIGH confidence: gpt-4.1 is the current default and generally available.

3. **Auth token has no expiry signal.** The `ghu_` token has no embedded expiry claim
   (unlike a JWT). Expiry is detected only when the API returns a 401/auth-error. The
   error-handling path must recognise this and surface a re-auth button, not just log an
   error.

4. **SDK is Technical Preview.** Wrap all SDK calls behind a thin service layer
   (`CopilotAuthManager`, `ChatCopilot`). If the SDK changes its interface, only those
   files need updating, not the graph or the HTTP layer.

---

## Sources

- [LibreChat GitHub — feature list](https://github.com/danny-avila/LibreChat)
- [Open WebUI vs AnythingLLM vs LibreChat 2026 — ToolHalla](https://toolhalla.ai/blog/open-webui-vs-anythingllm-vs-librechat-2026)
- [AI Chat UI Best Practices — DEV Community](https://dev.to/greedy_reader/ai-chat-ui-best-practices-designing-better-llm-interfaces-18jj)
- [react-markdown security and styling guide 2025 — Strapi](https://strapi.io/blog/react-markdown-complete-guide-security-styling)
- [Markdown chatbot with memoisation — Vercel AI SDK cookbook](https://ai-sdk.dev/cookbook/next/markdown-chatbot-with-memoization)
- [GitHub Copilot supported models — GitHub Docs](https://docs.github.com/en/copilot/reference/ai-models/supported-models)
- [GPT-4.1 now default in GitHub Copilot — GitHub Changelog](https://github.blog/changelog/2025-05-08-openai-gpt-4-1-is-now-generally-available-in-github-copilot-as-the-new-default-model/)
- [Interacting with LLMs with Minimal Chat — Eugene Yan](https://eugeneyan.com/writing/llm-ux/)
- [LLM Chat UI Concepts 2025 — Daniel Corin](https://www.danielcorin.com/posts/2025/llm-chat-ui-concepts/)
- [ChatGPT history UX case study — Ellie Kesha](https://shooka95k.com/portfolio-items/chat-gpt-history-and-chat-management-ux-case-study/)
- [Error Handling and Retries for LLM calls 2026 — Medium](https://medium.com/@sonitanishk2003/error-handling-retries-making-llm-calls-reliable-ee7722fc2ea9)
