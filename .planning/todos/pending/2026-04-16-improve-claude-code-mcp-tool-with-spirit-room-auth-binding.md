---
created: 2026-04-16T03:30:00.000Z
title: claude_code MCP ツールに spirit-room 方式の認証バインドとセキュリティ改善を適用
area: general
files:
  - mcp_server/tools/claude_code.py
  - docker-compose.yml
  - mcp_server/Dockerfile
---

## Problem

既存の `claude_code` MCP ツール (`mcp_server/tools/claude_code.py`) は:

- **認証なし**: env 許可リストが `PATH/HOME/LANG/LC_ALL/TERM` のみで、Claude CLI の認証情報が渡らない → CLI が `claude CLI not found` or 未認証で失敗
- **cwd が `/tmp`**: プロジェクトファイルにアクセスできない
- **権限無制限**: `--allowedTools` 指定なし → FS 全域に読み書き可能
- **タイムアウトが短い**: 60s 固定

`/home/parallels/workspaces/spirit-room-full` にて、Docker コンテナ内で Claude Code を安全に実行するパターンが確立されているので、その知見を取り込む。

## Solution

### 1. 認証バインド — Docker volume マウント

**ホスト側のファイル構成:**

```
~/.claude/                          # Claude Code の設定ディレクトリ
  .credentials.json                 # OAuth トークン (short-lived, 自動リフレッシュ)
    └── claudeAiOauth:
        ├── accessToken: sk-ant-oat01-...
        ├── refreshToken: sk-ant-ort01-...
        ├── expiresAt: epoch ms
        ├── scopes: [user:inference, user:sessions:claude_code, ...]
        └── subscriptionType: "max"

~/.claude.json                      # グローバル設定 (60KB+, 大部分は不要)
  └── oauthAccount:                 # ← これだけ必要
      ├── accountUuid
      ├── emailAddress
      ├── organizationUuid
      ├── displayName
      └── ...
```

**docker-compose.yml に追加する volume:**

```yaml
mcp-server:
  volumes:
    # 既存
    - ./mcp_server:/mcp_server
    - ./config:/mcp_server/config:ro
    - claude-code-outputs:/shared/claude-code-outputs
    # 追加: Claude Code 認証
    - ${HOME}/.claude:/root/.claude:ro           # credentials.json (RO)
    - ${HOME}/.claude.json:/root/.claude.json:ro # oauthAccount (RO)
```

### 2. env 許可リストの拡張

`claude_code.py` の `ALLOWED_ENV_KEYS` に追加:

```python
ALLOWED_ENV_KEYS = frozenset({
    "PATH", "HOME", "LANG", "LC_ALL", "TERM",
    "CLAUDE_CODE_BUBBLEWRAP",  # サンドボックスモード有効化
})
```

### 3. `--allowedTools` によるホワイトリスト

```python
proc = await asyncio.create_subprocess_exec(
    "claude",
    "--print", prompt,
    "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch",
    ...
)
```

spirit-room 方式: `--dangerously-skip-permissions` ではなく `--allowedTools` で最小権限。

### 4. cwd の見直し

`/tmp` → `/workspace` or `/app`（worker コンテナの作業ディレクトリ）に変更。
ただし SubAgent 経由で実行する場合、アクセスさせるディレクトリを限定する設計が必要。

### 5. タイムアウトの見直し

Claude Code の実行は 60s では不十分なケースがある。spirit-room は無制限だが、
MCP ツールとしては 120-180s が現実的。

### 6. Dockerfile 変更

mcp-server の Dockerfile に Claude Code CLI がインストールされていなければ追加:

```dockerfile
RUN npm install -g @anthropic-ai/claude-code
```

### spirit-room の参考実装パス

| ファイル | 内容 |
|----------|------|
| `spirit-room/spirit-room` (line 83, 148) | volume マウント定義 |
| `spirit-room/base/entrypoint.sh` (line 23-33) | symlink による credentials 共有 |
| `spirit-room/base/scripts/start-training-kaio.sh` (line 57-75) | oauthAccount マージ処理 |
| `spirit-room/base/Dockerfile` (line 47) | `npm install -g @anthropic-ai/claude-code` |

### 注意事項

- `.credentials.json` は RO マウント推奨 — MCP サーバーが書き換えるべきでない
- `~/.claude.json` は 60KB+ と大きいが、Claude CLI が `oauthAccount` を参照するために必要
- spirit-room の Kaio モードでは `oauthAccount` だけを `jq` で抽出してマージする手法もある — サイズが気になる場合はこの方式を検討
- `privileged: true` は既に `mcp_tools.yaml` に設定済み（今回の Session で追加）
