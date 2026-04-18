# 0043. チャット履歴の BaseMessage.content 正規化と ReactMarkdown 防御ガード（defense-in-depth）

**Date:** 2026-04-18
**Status:** Accepted

## Context

Phase 28（CodeAct SubAgent）導入以降、SuperChat でチャット履歴スレッドをクリックすると UI 全体が白画面になる不具合が報告された。

ブラウザ Console に次のアサーションが記録されていた:

```
Uncaught Assertion: Unexpected value [object Object] for children prop, expected string
```

原因は LangGraph チェックポイントから復元された `BaseMessage.content` が常に string とは限らないこと。

- `HumanMessage.content: str` — 常に string
- `AIMessage.content: str | list[dict]` — tool_use / CodeAct 結果を含む応答は `[{"type": "text", "text": "..."}, {"type": "tool_use", ...}]` のような **構造化 list**
- `ToolMessage.content: str | list[dict]` — ツール実行結果（ユーザー向けではない内部メッセージ）

`app/api/routes/chat.py::_messages_to_response` は `msg.content` をそのままレスポンス JSON の `entry["content"]` に詰めており、フロントの `MarkdownMessage` は型定義上は `content: string` を受け取るが、実行時には上記の object がそのまま流れ込んでいた。react-markdown は children が非 string の場合に throw するため、履歴ロードでコンポーネントツリー全体がアンマウント → 白画面になっていた。

既に DB（`public.checkpoints`）には構造化 content を持つチェックポイントが**多数蓄積されている**ため、新規リクエストの正規化だけでは過去スレッドが救えない。一方で、型システム上の契約（`ChatMessage.content: string`）を壊してフロント全面を書き換えるのも過剰。

## Decision

Defense-in-depth（二段構え）で修正する:

### 1. バックエンド — 根本治療（新規ストリーム）

`app/api/routes/chat.py` に純粋関数 `_normalize_content(content) -> str` を追加し、`_messages_to_response` を通る全応答を string に正規化する:

- `str` → そのまま返す
- `list[dict]` → `{"type": "text", "text": "..."}` ブロックだけ抽出し `\n` で連結。`tool_use` / `tool_result` / `image_url` などは **履歴 UI から捨てる**
- text ブロックが 1 つも無い構造化 content は `json.dumps(..., ensure_ascii=False)` でフォールバック（デバッグ可能性優先）
- `dict` / その他型も `json.dumps` → `str(...)` で必ず string を返す

同時に `_messages_to_response` のフィルタを `isinstance(msg, (SystemMessage, ToolMessage))` に拡張し、**ToolMessage を履歴から完全に除外**する（ツール実行の可視化はストリーミング中の `tool_executing` イベントで既に行っているため、履歴再表示では不要）。

Debate ブランチが持っていたインラインの同等ループは `_messages_to_response` 呼び出しに統合し、orchestrator / chat / debate 全 3 パスで正規化を一貫させた。

### 2. フロントエンド — 後方互換の防御層（既存スレッド）

DB に既に保存されている壊れたチェックポイントが API から流れてきた場合でも UI がクラッシュしないよう、フロントの**最後の砦**として実行時ガードを追加:

- `frontend/src/components/MarkdownMessage.tsx`: `safeContent = typeof content === 'string' ? content : JSON.stringify(content, null, 2)` を計算し、`<ReactMarkdown>` の children に `safeContent` を渡す
- `frontend/src/components/MessageArea.tsx::CopyAllButton`: `m.content.replace(...)` の前に同等の typeof ガード

`MarkdownMessageProps.content: string` / `ChatMessage.content: string` の型定義は**変更しない**。型契約上は string が正しく、フロントのガードはあくまで **DB 残留データに対する防御層**。

## Alternatives Considered

1. **フロントエンドのみの修正（バックエンド無変更）**
   - 却下: すべてのレンダリングポイント（MarkdownMessage, CopyButton, CopyAllButton, 将来の新 UI）で同じガードを複製する必要があり、抜け漏れの温床になる。また `content` が構造化 list の場合にテキスト部分だけ抜き出す意味的処理はバックエンドのほうが情報量を持っている（LangChain の message type に直接アクセスできる）。

2. **バックエンドのみの修正（フロント無変更）**
   - 却下: 既に DB に保存されている構造化 content はマイグレーションで直すのが困難（チェックポイント JSON の深い位置に埋まっている）。新規リクエストは救えても、過去スレッドの履歴クリックで白画面が残る。

3. **ToolMessage を履歴に残して整形表示する**
   - 却下: ツール実行結果はストリーミング中の `tool_executing` イベント / ステップ表示で既に可視化されており、履歴 UI に重複して出す UX 価値が低い。逆に長大な tool_result（検索結果 3000 tokens など）が履歴に混ざると可読性を損なう。除外が素直。

4. **`MarkdownMessageProps.content` を `string | unknown` に型緩和する**
   - 却下: 型契約を緩めると「契約違反のデータが流れてくる」のが正常系扱いになり、バックエンド正規化のインセンティブが失われる。型は string のままで、ランタイムガードは「防御のための例外処理」として位置づけるのが健全。

5. **チェックポイントマイグレーション（DB の構造化 content を string に書き戻す）**
   - 却下: LangGraph checkpoint の内部 JSON 構造に直接触るのはリスクが高く、今後の LangChain message schema 更新に追従しにくい。読み出し時正規化のほうが疎結合。

## Consequences

### Positive

- 白画面の primary bug が消え、過去スレッドの履歴クリックも安全になった
- ToolMessage が履歴 UI から除外されたことで、CodeAct / Web 検索スレッドの履歴が人間可読になった（tool_result の長文が混ざらない）
- orchestrator / chat / debate 全パスで正規化ロジックが共通化され、将来の新 message type 追加時も 1 箇所の修正で済む
- 型契約（`content: string`）を保ったまま、既存スレッドに対する後方互換を実現できた

### Negative / Gotchas

- **Debate ブランチの挙動差分（意図的）**: 従来 debate は `SystemMessage` も `ai` 扱いで履歴に出していたが、`_messages_to_response` 共通化後は SystemMessage と ToolMessage の両方がフィルタされる。debate で SystemMessage を可視化する要件があれば別途対応が必要（現状は無いと判断）。

- **構造化 content の text 部分のみ抽出という損失**: `tool_use` / `tool_result` / `image_url` などのブロックは履歴から完全に捨てられる。もし将来「履歴で画像を再表示したい」要件が出た場合は、`_normalize_content` の return 型を `str` から `str | list[Block]` に広げる必要がある（その場合は MarkdownMessage 側も構造化対応が必要になる）。

- **フロントエンドのガードは「出るべきでない」コードパス**: `safeContent` が JSON.stringify を実行したら、それはバックエンド正規化のバグか、新しい message type が追加されて正規化漏れがあることを意味する。運用時に `safeContent` が stringify フォールバックに落ちたことを検知できる仕組み（console.warn など）を将来足すとよい。

- **`GET /api/threads/{id}/messages` のレスポンス契約が明確化**: `messages[].content` は常に string であることを契約として固定した。他のクライアント（Canvas の iframe-rpc など）が将来このエンドポイントを叩く場合、この契約に依存できる。

- **修正対象外の既存 frontend TypeScript エラー**: 今回の修正中に、`MermaidBlock.tsx` が `html-to-image` を import しているが dev container の `node_modules` に未インストールという UAT 阻害バグも発覚した。これはスコープ外（`bun install` で解決、本 ADR の対象ではない）。

### Future-proofing

LangChain message schema は今後も拡張される可能性があるため（例: `multimodal_content`, `reasoning_blocks` など）、`_normalize_content` は **未知の型が来ても必ず string を返す** ように設計した（最終フォールバックで `str(content)` まで落ちる）。型追加時は `list` 分岐に新しい block type の抽出ロジックを足すことで拡張する。
