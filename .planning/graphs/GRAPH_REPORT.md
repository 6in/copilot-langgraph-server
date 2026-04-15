# Graph Report - .  (2026-04-15)

## Corpus Check
- 160 files · ~100,350 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1496 nodes · 2955 edges · 72 communities detected
- Extraction: 56% EXTRACTED · 44% INFERRED · 0% AMBIGUOUS · INFERRED: 1306 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]

## God Nodes (most connected - your core abstractions)
1. `ChatCopilot` - 72 edges
2. `RPCContext` - 72 edges
3. `SubAgentRegistry` - 72 edges
4. `ToolEnabledSubAgent` - 46 edges
5. `JobStore` - 42 edges
6. `AgentState` - 38 edges
7. `RouterNode` - 35 edges
8. `IframeRpcHandler` - 34 edges
9. `OrchestratorHandler` - 32 edges
10. `CopilotAuthManager` - 31 edges

## Surprising Connections (you probably didn't know these)
- `GemSubAgent — SubAgent implementation backed by a user-created Gem.  Used by Orc` --uses--> `SubAgent`  [INFERRED]
  app/orchestrator/gem_agent.py → super-agent-sample/src/agent.py
- `A SubAgent whose identity and behaviour come from a Gem record in the DB.      U` --uses--> `SubAgent`  [INFERRED]
  app/orchestrator/gem_agent.py → super-agent-sample/src/agent.py
- `RouterNode` --uses--> `ChatCopilot`  [INFERRED]
  super-agent-sample/src/graph.py → app/providers/copilot.py
- `SubAgentRegistry` --uses--> `ChatCopilot`  [INFERRED]
  super-agent-sample/src/agent.py → app/providers/copilot.py
- `Unit tests for ChatCopilot (app/providers/copilot.py).  Covers PROV-01, PROV-02,` --uses--> `ChatCopilot`  [INFERRED]
  tests/test_provider.py → app/providers/copilot.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (114): get_github_token(), get_jwt_payload(), execute_code_review(), コードレビュー用のスクリプト - Copilot SDK を使用          Args:         params: {             "c, execute_doc_gen(), ドキュメント自動生成用のスクリプト - Copilot SDK を使用          Args:         params: {, add_to_blocklist(), async_is_blocked() (+106 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (101): ABC, Abstract base class for pluggable worker task handlers., Interface every task handler must implement.      The worker facade calls handle, TaskHandler, _build_debate_turns(), DebateHandler, DebateGraph task handler — runs turn-based multi-agent debate via DebateGraph., AIMessage リストを {name, content} の発言リストに変換する。 (+93 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (93): auth_status(), logout(), Start GitHub Device Flow and return codes for the web UI.          Returns dict, poll_auth(), Auth API routes — Device Flow start/poll/status (AUTH-03).  Endpoints: - POST /a, Log out by revoking the JWT session cookie via Redis blocklist.      Reads JWT f, Return current authentication state based on JWT cookie.      Per D-04: Frontend, Start GitHub Device Flow. Returns user_code, verification_uri, and flow_id. (+85 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (75): CopilotAuthManager, CopilotAuthManager — Device Flow OAuth + Fernet token encryption.  AUTH-01: Devi, Perform GitHub Device Flow and return the access token.          Polls GITHUB_TO, Make a single poll attempt for Device Flow completion.          Returns (token,, Delete the encrypted token file from disk.          Returns True if the file was, Return a valid GitHub token.          Tries load_token() first; falls back to de, Manages GitHub OAuth authentication for Copilot.      Responsibilities:     - En, Return Fernet key bytes.          Priority:         1. COPILOT_TOKEN_ENC_KEY env (+67 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (79): from_http(), from_slack(), _keep_first(), Immutable request context threaded through all LangGraph nodes.      Fields:, Keeps the first-set context value; discards node overwrites.      LangGraph call, RPCContext, _extract_last_human_message(), _make_aggregator_node() (+71 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (65): SubAgent, BaseChatModel, ChatCopilot, ChatCopilot — BaseChatModel wrapper around the GitHub Copilot SDK.  Standalone c, Initialise CopilotClient if not already started.          SDK symbols are import, Convert a LangChain message list to a single prompt string.          Format::, LangChain-compatible wrapper for the GitHub Copilot SDK.      This is the ONLY f, Send messages to Copilot and return a ChatResult.          Creates a new session (+57 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (75): AppDefinition, AppRegistry, list_apps(), Application Package Registry — APP-01.  AppRegistry scans an apps/ directory for, Return all discovered app definitions, sorted by slug., Return the AppDefinition for the given slug, or None if not found., Return the agents list for the given app slug, or [] if not found., Parsed representation of a single APP.md package file. (+67 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (54): _check_agent_importable(), Attempt to import agent.py without instantiating ChatCopilot.      Loads the mod, build_canvas_graph(), build_graph(), LangGraph conversation graph builder.  Compiles a StateGraph with a single chatb, Build and compile the Canvas-specific conversation graph.      Identical to buil, Keep all messages but replace older HTML AI responses with a placeholder.      C, Build and compile the conversation graph once at startup.      Parameters     -- (+46 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (74): AgentHealth, AgentStatusEnum, from_dir(), _load_code_agent(), Return health status for all discovered agents (HEALTHY, DEGRADED, FAILED)., Load a code-type agent from agent.py in agent_dir.      Convention: agent.py mus, SubAgentRegistry, Enum (+66 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (79): claude_code(), Claude Code CLI ツール実装 (Phase 23 Plan 02).  CODE-01: claude_code ツール — asyncio.cr, Register claude_code tool on the given FastMCP instance., 4000 文字超の出力を shared volume に書き出し、ファイルパスを返す。      Args:         output: 全文出力（切り捨て, Claude Code CLI をサブプロセスとして実行する（CODE-01〜03）。      Args:         prompt: claude --, register_tools(), _save_overflow_output(), close_pools() (+71 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (59): MenuDispatcher, MenuRegistry, build_orchestrator_graph(), build_simple_graph(), fallback_node(), RouterNode, main(), AgentState (+51 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (60): list_agents(), Agents metadata endpoint.  Endpoint: - GET /api/agents — list available agents w, Return available agents by scanning AGENT_DIR for AGENT.md files.      Reads fro, create_thread(), delete_thread(), get_thread_messages(), list_threads(), Chat and thread API routes (CHAT-01, CHAT-02, CHAT-03, CHAT-04, ASYNC-01, ASYNC- (+52 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (46): appendMessage(), checkAuthStatus(), createNewThread(), deleteThread(), hideTyping(), loadThreads(), loadUserInfo(), performLogout() (+38 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (25): CanvasUpdateRequest, CanvasUploadRequest, deploy_app(), get_app(), get_canvas_gem_id(), get_source(), list_or_get_by_thread(), Canvas Apps API routes — HTML app storage, editing, and deployment (Phase 15). (+17 more)

### Community 14 - "Community 14"
Cohesion: 0.17
Nodes (23): ScriptBackend: load and execute tool scripts with INPUT_SCHEMA validation.  Tool, Load a tool script module and call its run() with validated input., Load script_path as a Python module, validate kwargs, call run().          Args:, ScriptBackend, Tests for ScriptBackend: INPUT_SCHEMA validation before run() call., ScriptBackend.call() on a tool without INPUT_SCHEMA succeeds (permissive)., Write a tool script to tmp_path and return its path., ScriptBackend.call() on a script without run() raises AttributeError. (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (25): Tests for /api/chat and /api/threads endpoints (CHAT-01..04, ASYNC-01).  /api/ch, GET /api/threads?app_id=superchat returns only superchat threads (API-01, FE-01), POST /api/chat returns job_id and thread_id immediately (ASYNC-01)., GET /api/threads without ?app_id returns all threads (backward compat, API-02)., POST /api/chat with mode='super' writes app_id='superchat' to threads (API-03, D, GET /api/threads returns threads even without checkpoints (API-01, DB-01)., POST /api/chat without session cookie returns 401 auth_required., POST /api/chat with missing message field returns 422 (CHAT-02). (+17 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (20): iframe_rpc(), IframeRpcRequest, IframeRpcResponse, Iframe JSON-RPC bridge endpoint (Phase 18, updated Phase 19).  POST /api/iframe-, Enqueue a JSON-RPC request from an iframe Canvas app.      Accepts a JSON-RPC st, _make_test_app(), Unit tests for POST /api/iframe-rpc endpoint., POST /api/iframe-rpc with null params passes empty dict as rpc_params. (+12 more)

### Community 17 - "Community 17"
Cohesion: 0.22
Nodes (19): create_gem(), delete_gem(), get_gem(), list_gems(), Gem CRUD API routes — AI persona management (Phase 15).  Endpoints: - POST   /ap, Get a specific Gem by ID (ownership enforced).      Returns 404 if gem does not, Update a Gem's fields (partial update, ownership enforced).      Only provided f, Delete a Gem (ownership enforced) (GEM-03).      Returns 404 if gem does not exi (+11 more)

### Community 18 - "Community 18"
Cohesion: 0.18
Nodes (5): agentAccentColor(), agentBgColor(), hashName(), chipSelectedFor(), AgentChip()

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (11): mock_llm(), Tests for LangGraph conversation graph (GRPH-01, GRPH-02, GRPH-03)., Mock BaseChatModel that returns a fixed AIMessage., GRPH-01: Second message sees full history (human + AI + human)., GRPH-02: Different thread_ids have independent histories., GRPH-03: Graph has chatbot node with START->chatbot->END edges., Basic: single message returns HumanMessage + AIMessage., test_extension_point() (+3 more)

### Community 20 - "Community 20"
Cohesion: 0.2
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.44
Nodes (7): dispatchFromIframe(), getPreviewIframe(), runAllTests(), testAI(), testInvalidOrigin(), testQueryInsertBlocked(), testQuerySelect()

### Community 22 - "Community 22"
Cohesion: 0.25
Nodes (7): Test stubs for Gem CRUD API — GEM-01, GEM-02, GEM-03.  Wave 0: stubs only. Imple, GEM-01: POST /api/gems creates a gem for authenticated user., GEM-02: GET /api/gems returns only the user's own gems., GEM-03: DELETE /api/gems/{id} returns 404 for another user's gem., test_create_gem(), test_delete_gem_ownership(), test_list_gems()

### Community 23 - "Community 23"
Cohesion: 0.25
Nodes (7): Test stubs for Canvas Apps API — CANVAS-01, CANVAS-02, CANVAS-03.  Wave 0: stubs, CANVAS-01: POST /api/canvas/apps/upload saves HTML., CANVAS-02: GET /api/canvas/apps/{app_id} returns correct HTML., CANVAS-03: POST /api/canvas/apps/{app_id}/deploy writes HTML file., test_deploy_app(), test_get_app(), test_upload_app()

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (5): Shared pytest fixtures for super-agent-sample unit tests., Create a temporary menus/ directory with super-chat.yaml and simple-chat.yaml., Create a temporary agents/ directory with code-reviewer and sql-analyst AGENT.md, tmp_agents_dir(), tmp_menus_dir()

### Community 25 - "Community 25"
Cohesion: 0.33
Nodes (5): Test stubs for LangGraph handler Canvas extension — WORKER-01, WORKER-02.  Wave, WORKER-01: LangGraphHandler extracts HTML from Canvas Gem thread and saves to ca, WORKER-02: extract_html() correctly extracts HTML block from markdown., test_canvas_gem_extraction(), test_extract_html()

### Community 26 - "Community 26"
Cohesion: 0.47
Nodes (5): get_job(), Job status polling endpoint (ASYNC-02).  GET /api/job/{job_id} — returns job sta, Return job status. pending if not yet complete, done with result if complete., JobStatusResponse, Response from GET /api/job/{job_id} — polling endpoint.

### Community 27 - "Community 27"
Cohesion: 0.4
Nodes (2): handleKeyDown(), handleSend()

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (3): Hosted Canvas Apps — dynamic hosting shell (Phase 19).  GET /apps/{app_id} — DB, Serve a deployed Canvas app as a standalone page (D-01, D-08).      Fetches HTML, serve_hosted_app()

### Community 29 - "Community 29"
Cohesion: 0.5
Nodes (3): Phase 22: Tavily web_search ツール実装。  web_search_stub の本番差し替え。TavilySearchResults, Phase 22: Tavily web_search ツールを登録する。, register_tools()

### Community 30 - "Community 30"
Cohesion: 0.5
Nodes (3): Stub tool implementations. Phase 22 moved web_search to tools/web_search.py (Tav, Register stub tools on the given FastMCP instance.      Phase 23 完了後の状況:     - p, register_tools()

### Community 31 - "Community 31"
Cohesion: 0.5
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 0.83
Nodes (3): ai(), _call(), query()

### Community 33 - "Community 33"
Cohesion: 0.67
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 0.67
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 0.67
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 0.67
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 0.67
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (2): handleIframeMessage(), _waitForJob()

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): ツール実行イベントを非同期コンテキスト経由で伝播させる ContextVar ヘルパー。

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Construct RPCContext from HTTP request fields.          Takes explicit kwargs ra

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Construct RPCContext from a Slack event payload.          thread_id uses thread_

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Execute the task.          Args:             ctx: arq worker context (redis_clie

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (0): 

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (0): 

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (0): 

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **296 isolated node(s):** `ChatCopilot — BaseChatModel wrapper around the GitHub Copilot SDK.  PROV-01: Imp`, `LangChain-compatible wrapper for the GitHub Copilot SDK.      This is the ONLY f`, `Send messages to Copilot and return a ChatResult.          Creates a new session`, `Stream tokens from Copilot using ASSISTANT_MESSAGE_DELTA events.          Uses s`, `Initialise CopilotClient if not already started.` (+291 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 39`** (2 nodes): `tool_context.py`, `ツール実行イベントを非同期コンテキスト経由で伝播させる ContextVar ヘルパー。`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (2 nodes): `SuperChatWrapper()`, `App.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (2 nodes): `useAgents.ts`, `useAgents()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (2 nodes): `useCanvas.ts`, `useCanvas()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (2 nodes): `useGems.ts`, `useGems()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (2 nodes): `useThreads.ts`, `useThreads()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (2 nodes): `ThemeContext.ts`, `useCurrentTheme()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (2 nodes): `handleCopy()`, `AuthPanel.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (2 nodes): `Header.tsx`, `handleLogout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (2 nodes): `SkeletonCard()`, `CanvasScreen.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Construct RPCContext from HTTP request fields.          Takes explicit kwargs ra`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Construct RPCContext from a Slack event payload.          thread_id uses thread_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Execute the task.          Args:             ctx: arq worker context (redis_clie`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `types.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `main.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `CanvasPane.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `ConfirmModal.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `MenuScreen.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SubAgentRegistry` connect `Community 8` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 10`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `RPCContext` connect `Community 4` to `Community 1`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `ChatCopilot` connect `Community 5` to `Community 1`, `Community 4`, `Community 7`, `Community 8`, `Community 10`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 87 inferred relationships involving `str` (e.g. with `._try_parse_tool_call()` and `lifespan()`) actually correct?**
  _`str` has 87 INFERRED edges - model-reasoned connections that need verification._
- **Are the 61 inferred relationships involving `ChatCopilot` (e.g. with `FastAPI application entry point.  Lifespan manages: - CopilotAuthManager instanc` and `Initialize and tear down shared resources.`) actually correct?**
  _`ChatCopilot` has 61 INFERRED edges - model-reasoned connections that need verification._
- **Are the 70 inferred relationships involving `RPCContext` (e.g. with `DebateState` and `app/orchestrator/debate_graph.py  DebateGraph — ターン制マルチエージェント会話グラフ  Exports:`) actually correct?**
  _`RPCContext` has 70 INFERRED edges - model-reasoned connections that need verification._
- **Are the 65 inferred relationships involving `SubAgentRegistry` (e.g. with `RouterNode` and `ChatCopilot`) actually correct?**
  _`SubAgentRegistry` has 65 INFERRED edges - model-reasoned connections that need verification._