# Deferred Items — Phase 05

## Pre-existing failures (out of scope for this phase)

### test_auth_poll_pending (tests/test_api_auth.py)
- **Status:** Failing before Phase 05 work began
- **Error:** `TypeError: cannot unpack non-iterable NoneType object` at `token, retry_after = await auth_manager.check_device_flow(device_code)`
- **Root cause:** `mock_auth_manager.check_device_flow` returns `None` but the route expects a tuple `(token, retry_after)`
- **Scope:** Pre-existing in Phase 03/04 work — not caused by Phase 05 changes
- **Action needed:** Fix `conftest.py` mock to return `(None, None)` or fix route to handle `None` return
