# Deferred Items — Phase 04 Plan 01

## Pre-existing Test Failures (out of scope for 04-01)

These failures existed before Plan 04-01 execution started. They are pre-existing issues NOT caused by this plan's changes.

### tests/test_api_auth.py::test_auth_poll_pending
- **Error:** `TypeError: cannot unpack non-iterable NoneType object` in `app/api/routes/auth.py:66`
- **Cause:** `conftest.py` fixture sets `manager.check_device_flow = AsyncMock(return_value=None)` but the route unpacks `token, retry_after = await auth_manager.check_device_flow(device_code)` — mock needs to return a tuple
- **Fix:** Update `mock_auth_manager` fixture to return `AsyncMock(return_value=(None, 5))` or fix the poll logic

### tests/test_api_auth.py::test_auth_poll_success_sets_cookie
- **Error:** `ValueError` (likely same tuple-unpack root cause or similar mock mismatch)
- **Cause:** Same root cause as above — mock return value mismatch

These should be fixed in a future quick task targeting `tests/conftest.py` mock_auth_manager fixture.
