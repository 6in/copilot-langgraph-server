# Roadmap: Copilot LangGraph Chat

## Overview

Three phases follow the strict dependency order the architecture demands: the Copilot SDK (highest risk, Technical Preview) is isolated and validated first, the LangGraph graph layer is built on top of a proven provider, and the FastAPI web layer plus vanilla JS frontend deliver the browser chat experience last. Each phase produces something independently runnable before the next layer is added.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Auth + Provider Foundation** - Copilot SDK isolated, Device Flow auth working, ChatCopilot gets a response end-to-end from a Python script
- [ ] **Phase 2: Graph Layer** - LangGraph StateGraph wired to ChatCopilot, multi-turn conversation history accumulates correctly, thread_id session isolation works
- [ ] **Phase 3: Web + Chat UI** - FastAPI serves the API, vanilla JS chat UI runs in the browser with full send/receive/history/auth flows

## Phase Details

### Phase 1: Auth + Provider Foundation
**Goal**: Developer can invoke ChatCopilot from a Python script and receive a Copilot response, with auth token persisted across restarts
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, PROV-01, PROV-02, PROV-03
**Success Criteria** (what must be TRUE):
  1. Running the auth script triggers Device Flow, opens a browser URL, and saves an encrypted token to ~/.copilot_sdk/token.enc
  2. Re-running the auth script reuses the saved token without re-prompting
  3. A Python script that creates ChatCopilot and calls ainvoke([HumanMessage("hello")]) receives a non-empty AIMessage response
  4. Changing the model parameter (e.g., gpt-4.1 vs claude-sonnet-4-5) produces a response without error
  5. CopilotClient start/stop lifecycle completes without subprocess leaks or warnings
**Plans:** 2/3 plans executed

Plans:
- [x] 01-01-PLAN.md — Project setup + CopilotAuthManager (Device Flow + Fernet encryption)
- [x] 01-02-PLAN.md — ChatCopilot BaseChatModel provider (SDK 0.2.0 wrapper)
- [ ] 01-03-PLAN.md — End-to-end validation script + live Copilot verification

### Phase 2: Graph Layer
**Goal**: Multi-turn conversation flows through a LangGraph StateGraph backed by ChatCopilot, with correct history accumulation and thread isolation
**Depends on**: Phase 1
**Requirements**: GRPH-01, GRPH-02, GRPH-03
**Success Criteria** (what must be TRUE):
  1. A second message in a conversation receives a reply that references context from the first message
  2. Two separate thread_ids maintain completely independent conversation histories
  3. Calling build_graph() once at startup and invoking it multiple times per thread does not recompile or recreate the graph
  4. The StateGraph structure has a clear extension point where tool-calling nodes could be added without rewiring the core graph
**Plans**: TBD

### Phase 3: Web + Chat UI
**Goal**: User can open a browser, authenticate via Device Flow, and hold a multi-turn chat conversation with Copilot
**Depends on**: Phase 2
**Requirements**: AUTH-03, CHAT-01, CHAT-02, CHAT-03, CHAT-04
**Success Criteria** (what must be TRUE):
  1. Opening the app in a browser and clicking "Login" triggers Device Flow and the page shows authenticated status after completion
  2. Sending a message shows a loading indicator, then displays the assistant reply in a message bubble
  3. Sending a follow-up message receives a reply that references the prior conversation context
  4. Assistant replies containing Markdown headers, bold text, or fenced code blocks render formatted — not as raw markup
  5. Clicking "New Chat" clears the message list and the next message starts a fresh conversation with no prior context
  6. When the Copilot token is expired, the UI shows a Re-authenticate button instead of a generic error
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auth + Provider Foundation | 2/3 | In Progress|  |
| 2. Graph Layer | 0/? | Not started | - |
| 3. Web + Chat UI | 0/? | Not started | - |
