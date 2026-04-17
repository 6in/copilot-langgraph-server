# 0040. UI 改善バッチ — Mermaid 画像コピー・スレッド日付グループ・Device Flow UX・ツールカタログ埋め込み

**Date:** 2026-04-17
**Status:** Accepted

## Context

4 つの独立した UI/DX 改善 todo を一括で対応した。いずれも既存機能の使い勝手を向上させる小〜中規模の変更で、相互依存がないためワークツリー並列で実装した。

1. **Mermaid View コピー**: Copy ボタンがソーステキストしかコピーできず、描画済みダイアグラムを画像として共有できなかった
2. **スレッドサイドバー**: フラットリストで日付区切りがなく、スレッド数が増えると探しにくかった
3. **Device Flow Copy**: コードコピー後に手動で GitHub URL を開く手間があった
4. **iframe-rpc.js ツール一覧**: Canvas アプリ開発者がどの MCP ツールが利用可能か知る手段がなかった

## Decision

### Mermaid 画像コピー (`html-to-image`)

- `html-to-image` ライブラリの `toPng` を採用。foreignObject を含む SVG を DOM レベルで PNG 変換できる
- View モードの Copy ボタンでコンテナ div を一時的に `fit-content` に縮小してキャプチャし、直後に元のスタイルを復元する方式
- `pixelRatio: 3` で高解像度キャプチャ（貼り付け先で拡大しても文字が読める）
- `skipFonts: true` で cross-origin CSS（Monaco Editor, Google Fonts）の SecurityError を回避
- 画像コピー失敗時はソーステキストコピーにフォールバック

### スレッド日付グループ

- `updated_at` 基準で「今日/昨日/今週/先週/それ以前」の 5 グループに分類
- 水平線 + 中央ラベルの区切りヘッダー（ChatGPT/Claude.ai 風）
- 「それ以前」グループはデフォルト折りたたみ、クリックで展開
- フロントエンドのみの変更（API 側のページネーションは見送り）

### Device Flow Copy & Open

- `handleCopy` に `window.open(verification_uri, '_blank')` を追加。click handler 内なのでポップアップブロッカーに引っかからない
- ボタンラベルを「Copy & Open」に変更

### iframe-rpc.js ツールカタログ

- `config/mcp_tools.yaml` のツール情報を `AVAILABLE_TOOLS` 定数 + JSDoc テーブルとして `iframe-rpc.js` に埋め込み
- `// --- BEGIN/END TOOL_CATALOG ---` マーカーで囲み、`scripts/sync-tool-list-to-js.py` で自動更新可能に

## Alternatives Considered

### Mermaid 画像コピー

- **Canvas API 直接描画**: mermaid SVG の foreignObject が Canvas を taint するため不可
- **SVG から foreignObject 除去**: テキスト変換が複雑で、絵文字やリッチテキストが失われる
- **サーバーサイド変換 (puppeteer)**: インフラ負荷が重く、200名規模の社内ツールには過剰
- **SVG 要素を直接 `toPng` ターゲット**: SVG が `width="100%" height="100%"` の相対サイズで、html-to-image が正しいピクセルサイズを取得できなかった
- **内側ラッパー div に ref**: レイアウトが崩れ、リサイズハンドルによるサイズ追随が効かなくなった

### スレッド日付グループ

- **API ページネーション**: 200名規模では当面不要と判断。将来スレッド数が大幅に増えた場合に検討

## Consequences

### Positive

- Mermaid ダイアグラムを Slack/Teams/ドキュメントに画像として直接貼り付け可能に
- スレッド一覧の視認性が大幅向上（日付コンテキスト + 古いスレッドの折りたたみ）
- Device Flow ログインが 1 クリックで完結（コピー + URL オープン）
- Canvas アプリ開発者が利用可能ツールをコード内で参照可能に

### Negative / Gotchas

- `html-to-image` は約 30KB の追加バンドルサイズ（Mermaid 本体 ~1MB に比べれば軽微）
- `skipFonts: true` により、キャプチャ画像ではカスタム Web フォントが反映されない（mermaid のデフォルトフォントは問題なし）
- 一時スタイル変更中に一瞬レイアウトがちらつく可能性がある（実用上は気にならないレベル）
- `AVAILABLE_TOOLS` はチャット AI の応答には反映されない（iframe アプリ内のコード参照用）。AI にツール一覧を答えさせるには Canvas エージェントのシステムプロンプトへの記載が別途必要
