# Phase 23 Deferred Items

## Out-of-scope issues discovered during execution

### [Phase 22 Bug] test_web_search_normal / test_web_search_truncates_content / test_web_search_error_handling

- **Found during:** Task 1 (TDD GREEN run)
- **File:** `tests/test_mcp_server.py`
- **Issue:** `patch("tools.web_search.TavilySearchResults")` fails with `AttributeError` because `TavilySearchResults` is imported locally inside the function body in `mcp_server/tools/web_search.py` (line 28), not at module level. The mock patch target does not exist as a module attribute.
- **Root cause:** Phase 22 implementation placed the import inside `try:` block, making it a local import that is not patchable via `unittest.mock.patch` at module level.
- **Fix required:** Move `from langchain_community.tools.tavily_search import TavilySearchResults` to module level in `mcp_server/tools/web_search.py`, or change the mock target to `langchain_community.tools.tavily_search.TavilySearchResults`.
- **Phase scope:** Phase 22 (pre-existing, not introduced by Phase 23)
- **Priority:** Low (tests were silently skipped/failing before Phase 23 changes)
