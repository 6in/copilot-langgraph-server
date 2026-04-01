---
phase: quick
plan: 260401-lkq
type: execute
wave: 1
depends_on: []
files_modified:
  - app/auth/jwt_utils.py
  - app/auth/manager.py
  - app/api/models.py
  - app/api/routes/auth.py
  - app/api/routes/chat.py
  - app/api/main.py
  - static/app.js
  - pyproject.toml
  - tests/test_jwt_auth.py
autonomous: true
must_haves:
  truths:
    - "Each user gets their own JWT after Device Flow, stored as httpOnly cookie"
    - "Chat requests are scoped to the authenticated user's GitHub token"
    - "Logout invalidates the JWT via in-memory blocklist"
    - "Multiple users can authenticate and chat independently"
    - "Server restart clears blocklist but does not break active JWTs (they just work until expiry)"
  artifacts:
    - path: "app/auth/jwt_utils.py"
      provides: "JWT encode/decode + Fernet token encryption + blocklist"
      exports: ["create_jwt", "decode_jwt", "encrypt_github_token", "decrypt_github_token", "add_to_blocklist", "is_blocked"]
    - path: "app/api/routes/auth.py"
      provides: "Updated auth routes with per-user JWT flow"
    - path: "app/api/routes/chat.py"
      provides: "JWT-protected chat routes extracting user token from JWT"
    - path: "tests/test_jwt_auth.py"
      provides: "Unit tests for JWT utilities"
  key_links:
    - from: "app/api/routes/auth.py (poll_auth)"
      to: "app/auth/jwt_utils.py (create_jwt)"
      via: "On Device Flow success, encrypts github_token into JWT, sets httpOnly cookie"
    - from: "app/api/routes/chat.py"
      to: "app/auth/jwt_utils.py (decode_jwt + decrypt_github_token)"
      via: "FastAPI Depends extracts JWT from cookie, decrypts github_token for ChatCopilot"
    - from: "app/api/routes/auth.py (logout)"
      to: "app/auth/jwt_utils.py (add_to_blocklist)"
      via: "Adds JWT jti to in-memory blocklist set"
---

<objective>
Migrate from single-user global auth state to per-user JWT-based authentication.

Purpose: Enable multiple users to authenticate independently via Device Flow, each getting a JWT containing their encrypted GitHub token. Eliminates global `app.state.auth_expired`, `app.state.device_flows["current"]`, and single-user `token.enc` file dependency for web auth.

Output: JWT auth middleware, updated auth/chat routes, in-memory logout blocklist, frontend cookie-based auth.
</objective>

<execution_context>
@.planning/quick/260401-lkq-jwt/260401-lkq-PLAN.md
</execution_context>

<context>
@CLAUDE.md
@app/auth/manager.py
@app/api/routes/auth.py
@app/api/routes/chat.py
@app/api/models.py
@app/api/main.py
@app/providers/copilot.py
@static/app.js
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create JWT utilities module + add PyJWT dependency</name>
  <files>app/auth/jwt_utils.py, pyproject.toml, tests/test_jwt_auth.py</files>
  <action>
1. Add `PyJWT>=2.9.0` to `pyproject.toml` dependencies, then run `uv sync`.

2. Create `app/auth/jwt_utils.py` with:

   **JWT secret management:**
   - `_get_jwt_secret() -> str`: Read from `JWT_SECRET` env var. If not set, read from `~/.copilot_sdk/.jwt_secret` file. If file doesn't exist, generate a 32-byte random hex string, write to file with chmod 0o600, return it.

   **Fernet encryption for GitHub tokens in JWT payload:**
   - Reuse the same Fernet key strategy as `CopilotAuthManager._get_or_create_fernet_key()` (env var `COPILOT_TOKEN_ENC_KEY` or file `~/.copilot_sdk/.enc_key`).
   - `encrypt_github_token(token: str) -> str`: Encrypt with Fernet, return base64 string.
   - `decrypt_github_token(encrypted: str) -> str`: Decrypt Fernet token, return raw `ghu_` token.

   **JWT creation and validation:**
   - `create_jwt(github_token: str, expires_minutes: int = 1440) -> str`: Create JWT with payload `{"sub": "copilot_user", "github_token": encrypt_github_token(github_token), "jti": uuid4().hex, "exp": now + expires_minutes}`. Sign with HS256 using `_get_jwt_secret()`.
   - `decode_jwt(token: str) -> dict`: Decode and verify JWT. Raise `jwt.ExpiredSignatureError` or `jwt.InvalidTokenError` on failure. After decode, check `is_blocked(payload["jti"])` -- raise `jwt.InvalidTokenError("Token revoked")` if blocked.

   **In-memory logout blocklist:**
   - Module-level `_blocklist: set[str] = set()` storing JTI strings.
   - `add_to_blocklist(jti: str) -> None`: Add JTI to set.
   - `is_blocked(jti: str) -> bool`: Check membership.
   - Note in docstring: blocklist is in-memory, clears on server restart. Acceptable for personal tool.

3. Create `tests/test_jwt_auth.py`:
   - Test `create_jwt` + `decode_jwt` roundtrip returns correct payload fields.
   - Test expired JWT raises `ExpiredSignatureError` (use `expires_minutes=-1` or mock time).
   - Test blocklisted JTI raises `InvalidTokenError`.
   - Test `encrypt_github_token` + `decrypt_github_token` roundtrip.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && uv run pytest tests/test_jwt_auth.py -x -v</automated>
  </verify>
  <done>JWT utility module exists with encode/decode/encrypt/decrypt/blocklist functions. All tests pass. PyJWT is installed.</done>
</task>

<task type="auto">
  <name>Task 2: Update auth routes for per-user JWT flow</name>
  <files>app/api/routes/auth.py, app/api/models.py, app/api/main.py</files>
  <action>
1. **Update `app/api/models.py`:**
   - Add `token` field (optional str) to `AuthPollResponse` -- returned only on success for cookie setting awareness, but actual cookie is set server-side via `Set-Cookie` header.
   - Add `username` field (optional str) to `AuthStatusResponse` -- for future multi-user display.

2. **Update `app/api/routes/auth.py`:**

   **`start_auth` (POST /api/auth/start):**
   - Generate a unique `flow_id = uuid4().hex` for this Device Flow session.
   - Store `device_flows[flow_id] = device_code` on `app.state.device_flows` (replacing `"current"` key pattern).
   - Return `flow_id` in `AuthStartResponse` (add `flow_id: str` field to model).

   **`poll_auth` (GET /api/auth/poll):**
   - Accept `flow_id` as query parameter: `flow_id: str = Query(...)`.
   - Look up `device_code = app.state.device_flows.get(flow_id)`.
   - On success (token obtained):
     - Create JWT via `create_jwt(token)`.
     - Build `JSONResponse` with `AuthPollResponse(done=True)` data.
     - Set httpOnly cookie: `response.set_cookie(key="session", value=jwt_token, httponly=True, samesite="lax", max_age=86400, path="/")`.
     - Clean up `device_flows[flow_id]`.
     - Return the JSONResponse (not the Pydantic model directly, since we need to set cookies on the response object).
   - On pending/error: return `AuthPollResponse` as before but use `flow_id` for lookup.

   **`logout` (POST /api/auth/logout):**
   - Read JWT from `request.cookies.get("session")`.
   - If JWT exists, decode it (catch errors silently), extract `jti`, call `add_to_blocklist(jti)`.
   - Build `JSONResponse` with logout success message.
   - Delete cookie: `response.delete_cookie(key="session", path="/")`.
   - Do NOT call `auth_manager.logout()` (token.enc is for CLI use, not web sessions).
   - Do NOT call `llm.close()` (LLM is no longer global per-user state).
   - Return the JSONResponse.

   **`auth_status` (GET /api/auth/status):**
   - Read JWT from `request.cookies.get("session")`.
   - Try `decode_jwt(token)` -- if succeeds, return `AuthStatusResponse(authenticated=True, expired=False)`.
   - If `ExpiredSignatureError`: return `authenticated=False, expired=True`.
   - If no cookie or `InvalidTokenError`: return `authenticated=False, expired=False`.
   - Remove dependency on `auth_manager.load_token()` and `app.state.auth_expired`.

   **Imports needed:** `from fastapi import Query`, `from fastapi.responses import JSONResponse`, `from app.auth.jwt_utils import create_jwt, decode_jwt, add_to_blocklist, decrypt_github_token`.

3. **Update `app/api/main.py`:**
   - Remove `app.state.auth_expired = False` from lifespan (no longer needed).
   - Keep `app.state.device_flows = {}` (still needed, but now keyed by flow_id not "current").
   - Keep `app.state.auth_manager` (still needed for `start_device_flow` and `check_device_flow`).
   - Keep `app.state.llm` -- but it will be used differently in Task 3.

4. **Update `AuthStartResponse` in models.py:**
   - Add `flow_id: str` field.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && uv run python -c "from app.api.routes.auth import router; print('Auth routes import OK')" && uv run python -c "from app.api.models import AuthStartResponse, AuthPollResponse, AuthStatusResponse; print('Models import OK')"</automated>
  </verify>
  <done>Auth routes use JWT cookies instead of global state. Device flows keyed by flow_id. Logout uses blocklist. Status checks JWT cookie.</done>
</task>

<task type="auto">
  <name>Task 3: Update chat routes to extract token from JWT + per-request ChatCopilot</name>
  <files>app/api/routes/chat.py, app/api/main.py, app/providers/copilot.py</files>
  <action>
1. **Create a FastAPI dependency in `app/api/routes/chat.py`:**

   ```python
   from fastapi import Depends, HTTPException, Request
   from app.auth.jwt_utils import decode_jwt, decrypt_github_token
   import jwt

   async def get_github_token(request: Request) -> str:
       """Extract and decrypt GitHub token from JWT cookie."""
       session_cookie = request.cookies.get("session")
       if not session_cookie:
           raise HTTPException(status_code=401, detail="auth_required")
       try:
           payload = decode_jwt(session_cookie)
           return decrypt_github_token(payload["github_token"])
       except jwt.ExpiredSignatureError:
           raise HTTPException(status_code=401, detail="auth_expired")
       except jwt.InvalidTokenError:
           raise HTTPException(status_code=401, detail="auth_invalid")
   ```

2. **Update `send_message` route:**
   - Add `github_token: str = Depends(get_github_token)` parameter.
   - Instead of using `request.app.state.llm` (global single-user LLM), create a per-request `ChatCopilot` instance: `llm = ChatCopilot(github_token=github_token, model=body.model)`.
   - Use the graph but with this per-request LLM. Since the graph is compiled with a fixed LLM, we need a different approach:
     - Option: Rebuild graph per request (wasteful) OR
     - Better option: Use the existing `app.state.graph` but override the LLM model. Since ChatCopilot is stored in the graph's node closure, we need to set the token on it before invoke.
     - Simplest correct approach: Before `graph.ainvoke()`, set `request.app.state.llm.github_token = github_token` and `request.app.state.llm.model = body.model`, then call `await request.app.state.llm.close()` to force re-init with new token. This is sequential (one request at a time) which is fine for a personal tool.
   - Remove the `auth_expired` flag logic from the except block. Instead, if SDK auth errors occur, just return the error -- the JWT middleware handles auth state.
   - Keep the `error="auth_expired"` response format so frontend still handles it.

3. **Update `app/api/main.py` lifespan:**
   - Remove `app.state.auth_expired = False` line.
   - Keep all other state (graph, checkpointer, auth_manager, llm, db_path, device_flows).

4. **Important: thread/message routes (list_threads, get_thread_messages, create_thread, delete_thread) do NOT need JWT protection** for now -- they are read/write operations on the local SQLite, and this is a personal tool. Add a comment noting this is intentional.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && uv run python -c "from app.api.routes.chat import router, get_github_token; print('Chat routes import OK')"</automated>
  </verify>
  <done>Chat route extracts GitHub token from JWT cookie. Per-request token injection into ChatCopilot. No global auth_expired flag.</done>
</task>

<task type="auto">
  <name>Task 4: Update frontend to handle JWT cookie auth + flow_id</name>
  <files>static/app.js</files>
  <action>
1. **Update `startAuthFlow()`:**
   - Store `flow_id` from the `/api/auth/start` response: `const flowId = data.flow_id;`
   - Pass `flowId` to `pollAuth` calls. Change the polling setup to: `authPollInterval = setInterval(() => pollAuth(flowId), 5000);`

2. **Update `pollAuth(flowId)`:**
   - Change fetch URL to include flow_id: `fetch('/api/auth/poll?flow_id=' + flowId)`
   - On `data.done === true`: the JWT cookie is set automatically by the browser from the `Set-Cookie` response header. Just hide auth panel and call `checkAuthStatus()`. Remove `location.reload()` -- the cookie is already set, just update UI state.

3. **Update `checkAuthStatus()`:**
   - No changes needed -- `/api/auth/status` now reads from the cookie server-side. The frontend fetch automatically sends cookies.

4. **Update `performLogout()`:**
   - No changes to the fetch call -- `/api/auth/logout` reads the cookie server-side and deletes it via `Set-Cookie`.
   - The browser automatically removes the cookie from the `Set-Cookie` delete response.

5. **Update `sendMessage()`:**
   - Handle 401 responses from `/api/chat`:
     - If `resp.status === 401`, parse the response, check `detail`:
       - `"auth_expired"` or `"auth_required"`: call `checkAuthStatus()` and show appropriate error message.
     - This replaces the `data.error === 'auth_expired'` check (keep that check too as fallback for non-401 auth errors).

6. **Remove global `isAuthenticated` guard in `sendMessage()`:**
   - The server now enforces auth via JWT cookie. The client-side `isAuthenticated` check can remain as a UX optimization (prevents unnecessary requests), but the source of truth is the server.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && grep -q "flow_id" static/app.js && grep -q "pollAuth(flowId)" static/app.js && echo "Frontend updated OK"</automated>
  </verify>
  <done>Frontend passes flow_id to poll endpoint. Auth state managed via httpOnly cookies. 401 handling in sendMessage.</done>
</task>

<task type="auto">
  <name>Task 5: Integration smoke test + cleanup</name>
  <files>tests/test_jwt_auth.py</files>
  <action>
1. **Add integration tests to `tests/test_jwt_auth.py`:**
   - Test auth status endpoint returns `authenticated=False` when no cookie.
   - Test auth status endpoint returns `authenticated=True` when valid JWT cookie is set.
   - Test auth status endpoint returns `expired=True` when expired JWT cookie is set.
   - Test chat endpoint returns 401 when no cookie.
   - Test logout endpoint clears cookie and blocklists JTI.
   - Use `httpx.AsyncClient` with `ASGITransport(app=app)` pattern (same as existing tests in the project).
   - Mock `auth_manager.start_device_flow` and `auth_manager.check_device_flow` as needed.
   - For cookie tests: manually set cookies on the httpx client using `cookies={"session": jwt_token}`.

2. **Run full test suite** to ensure no regressions.

3. **Verify imports are clean** -- no unused imports, no circular dependencies.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && uv run pytest tests/ -x -v</automated>
  </verify>
  <done>All tests pass including JWT roundtrip, auth endpoint integration tests, and existing tests. No regressions.</done>
</task>

</tasks>

<verification>
1. `uv run pytest tests/ -x -v` -- all tests pass
2. `uv run python -c "from app.api.main import app; print('App loads OK')"` -- app imports cleanly
3. Manual: start server with `uv run uvicorn app.api.main:app`, open browser, verify Device Flow -> JWT cookie -> chat works
</verification>

<success_criteria>
- JWT-based auth replaces global `app.state.auth_expired` flag
- Device flows keyed by unique flow_id (not "current")
- GitHub token encrypted in JWT payload via Fernet
- httpOnly cookie for session management
- In-memory blocklist for logout (no Redis)
- Frontend sends flow_id to poll endpoint
- Chat route extracts token from JWT cookie per-request
- All existing and new tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/260401-lkq-jwt/260401-lkq-SUMMARY.md`
</output>
