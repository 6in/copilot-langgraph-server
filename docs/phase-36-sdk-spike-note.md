# Phase 36 SDK Spike Note

**Date:** 2026-04-24
**Environment:** docker compose (local) / worker service / model `claude-sonnet-4.6`
**SDK:** github-copilot-sdk==0.2.0

## Verdict

**PASS** ✓ — SDK が `/shared/thread-files/_spike/_t/sample.txt` を path 経由で
open し、Copilot model (`claude-sonnet-4.6`) に送信、ファイル内容を反映した
要約 ("Phase 36 スパイクテストであることを示す1行のテキストファイルです") を
返した。A3 risk (FileAttachment.path mount/permission) clear、D-09 方針
(path-based attachments) のまま Wave 1 Plan 02 着手 OK。

## Setup

- Sample file: `/shared/thread-files/_spike/_t/sample.txt`
  (contents: "Phase 36 spike test. ファイルの内容はこれです。")
- Volume mount: `worker` サービスは `thread-files:/shared/thread-files:ro` で
  RO mount 済 (docker-compose.yml L117)
- Token: `app/auth/manager.py` の `CopilotAuthManager.load_token()` が返す
  ローカル保存済み Device Flow token を使用 (smoke 用、CI では走らせない)

## Command

```bash
# 1. spike 用テストファイル作成 (api コンテナ — RW mount)
docker compose exec api mkdir -p /shared/thread-files/_spike/_t/
docker compose exec api sh -c "echo 'Phase 36 spike test. ファイルの内容はこれです。' > /shared/thread-files/_spike/_t/sample.txt"

# 2. spike script 作成 (host 側、tests/_spike_attachments.py)
#    内容は本ドキュメント末尾 §Appendix A を参照

# 3. worker コンテナで spike 実行
docker compose exec worker uv run python tests/_spike_attachments.py

# 4. 終了後の片付け (必須)
docker compose exec api rm -rf /shared/thread-files/_spike
rm -f tests/_spike_attachments.py
```

## Observed Response

```
CONTENT: **要約:**

「Phase 36 スパイクテスト」であることを示す1行のテキストファイルです。
実質的な内容はその1文のみで、ファイルの内容を自己言及する形で記述されています。
```

(token / 社内機密の混入無し — model 応答のみを目視確認済み)

## Verdict Rationale

- **PASS 判定根拠**: 要約が sample.txt の実コンテンツ ("Phase 36 spike test" /
  "ファイルの内容はこれです") を明示的に参照しており、SDK subprocess が
  worker コンテナ内 RO mount 上の path から `open()` できていることを確認。
  - mount: `worker` 側 `/shared/thread-files/_spike/_t/sample.txt` を `ls -la`
    で `-rw-r--r-- 1 root root 61 Apr 24 01:37` として可視 (RO で read 可)
  - SDK: `session.send_and_wait(prompt, attachments=[FileAttachment(...)],
    timeout=60.0)` が timeout / PermissionError 無く完走
  - response: `response.data.content` に要約文字列が格納されている
- A3 risk (path mount / SDK file open) ⇒ **clear**, D-09 (path-based
  attachments) ⇒ **維持**, Wave 1 Plan 02 で workaround 不要

## Next-Wave Impact

- **PASS:** Wave 1 Plan 02 で `ChatCopilot._extract_attachments` →
  `session.send_and_wait(attachments=[FileAttachment(path=..., displayName=...)])`
  の配線を予定通り実装する。`displayName` は SDK 0.2.0 で **required**
  (Wave 0 Plan 01 Task 2 で確認 — SDK isolation test 経由) のため、
  D-15 の変換ルールで必ず埋める。
- **[SDK API 訂正] CopilotClient construction**: 当初の Appendix A は
  `CopilotClient(github_token=token)` と書いていたが、SDK 0.2.0 の正しい
  シグネチャは `CopilotClient(SubprocessConfig(github_token=token,
  use_logged_in_user=False))` (既存 `app/providers/copilot.py:301` と同形式)。
  Wave 1 Plan 02 で `ChatCopilot.__init__` を新規生成する経路を書く際は
  `SubprocessConfig` 経由のコンストラクタを使うこと。spike 中に判明、Appendix A
  も訂正済み (下記)。
- **[Auth API 注記] load_token() は sync, get_token() は async**:
  `CopilotAuthManager.load_token()` は同期 (`Optional[str]` を返す) で、
  spike script は `auth.load_token()` (no await) で正しい。一方、production
  経路 (worker / handler / provider) では token refresh + Device Flow 再開
  も含む `await self.auth_manager.get_token()` (async — `app/auth/manager.py:245`)
  を使う。spike 専用 script と production 配線で API を取り違えないこと。
- **FAIL:** Wave 1 開始前にユーザーと設計見直し
  - 候補 1: BlobAttachment 経由 (base64 in-memory) に切替え (D-09 で defer 中)
  - 候補 2: worker の thread-files mount を RW に変更してシンボリックリンク経由
  - 候補 3: SDK version pin 見直し / upstream issue 起票

---

## Appendix A: spike script (`tests/_spike_attachments.py`)

> **API 訂正履歴 (2026-04-24 spike 実行時):** 当初テンプレートは
> `CopilotClient(github_token=token)` と書いていたが、SDK 0.2.0 の正しい
> シグネチャは `CopilotClient(SubprocessConfig(github_token=..., use_logged_in_user=...))`。
> 実行時に発見し下記コードに反映済み (既存 `app/providers/copilot.py:301`
> も同形式)。`load_token()` は **sync** (no await) のため `auth.load_token()`
> で正しい。

```python
import asyncio
from copilot import CopilotClient, PermissionHandler, SubprocessConfig
from app.auth.manager import CopilotAuthManager


async def main() -> None:
    auth = CopilotAuthManager()
    token = auth.load_token()  # sync — load_token() is NOT async
    if token is None:
        raise RuntimeError(
            "No Copilot token found. Run Device Flow login first."
        )
    client = CopilotClient(
        SubprocessConfig(github_token=token, use_logged_in_user=False)
    )
    await client.start()
    try:
        session = await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            model="claude-sonnet-4.6",
        )
        response = await session.send_and_wait(
            "以下に添付したテキストファイルの内容を要約してください。",
            attachments=[
                {
                    "type": "file",
                    "path": "/shared/thread-files/_spike/_t/sample.txt",
                    "displayName": "sample.txt",
                }
            ],
            timeout=60.0,
        )
        print(
            "CONTENT:",
            response.data.content if response and response.data else None,
        )
        await session.disconnect()
    finally:
        await client.stop()


asyncio.run(main())
```

> このスクリプトは **spike 専用** で git に残さない。実行後は必ず削除すること
> (`rm -f tests/_spike_attachments.py`). 2026-04-24 の smoke 実行後、
> spike 用一時ファイル (`/shared/thread-files/_spike/`) と script 本体は
> 既に削除済み。

## Appendix B: 想定されるエラーと初期切り分け

| 症状 | 想定原因 | 初期切り分け |
|------|---------|------------|
| `PermissionError: [Errno 13]` on path | mount mode 不整合 | `docker compose exec worker stat /shared/thread-files/_spike/_t/sample.txt` で permission 確認 |
| `attachment file not found` | path mismatch | `docker compose exec worker ls -la /shared/thread-files/_spike/_t/` で worker から見えるか確認 |
| `auth required` / 401 | token 期限切れ | `app/auth/manager.py` で device flow 再実行 |
| timeout (60s) | SDK subprocess hang | `docker compose logs worker` で SDK subprocess の stderr を確認 |
| `model not supported` | model id 不正 | `await client.list_models()` でカタログを確認し vision 対応 model に切替え |

---

*Phase 36 Wave 0 Plan 01 Task 3 — A3 risk + SDK subprocess 実機確認 gate*
*Smoke 実行: 2026-04-24 / Verdict: PASS / Wave 1 Plan 02 着手 OK*
