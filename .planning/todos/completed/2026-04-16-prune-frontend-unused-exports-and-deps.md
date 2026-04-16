---
created: 2026-04-16T00:00:00.000Z
title: knip 指摘の frontend 未使用 export / 依存を削除
area: ui
files:
  - frontend/package.json
  - frontend/src/api/client.ts
  - frontend/src/hooks/useAuth.ts
  - frontend/src/utils/markdownTable.ts
---

## Problem

`.planning/reports/2026-04-16-cleanup-inventory.md` §4 を参照。
`bunx knip` の指摘:

- **未使用依存**: `rehype-highlight` (MarkdownMessage は Monaco 描画なので不要)
- **未使用 export**: `getThreadMessages` / `getCanvasApp` / `postIframeRpc` (`src/api/client.ts`)
- **未使用型**: `IframeRpcResponse` (`client.ts`), `AuthState` (`useAuth.ts`)
- **未使用定数 export**: `AG_GRID_THRESHOLD_ROWS`, `AG_GRID_THRESHOLD_COLS` (`markdownTable.ts` — 内部定数で十分)

## Solution

1. `bun remove rehype-highlight`
2. `src/api/client.ts` の未使用 function / type を削除（呼び出し元が本当に無いことを `rg` で再確認）
3. `markdownTable.ts` の閾値定数の export を外し、ファイル内 const に戻す
4. `bun run build` で型エラーなし、`bunx knip` の出力が縮小することを確認

優先度: 低（動作には影響しないが、将来の混乱を減らす）
