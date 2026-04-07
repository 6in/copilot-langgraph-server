# 0013. Agent Identity in Chat UI — Per-Agent Color and Name Display

**Date:** 2026-04-08  
**Status:** Accepted

## Context

SuperChat マルチエージェント応答では、複数の GEM（エージェント）が順番に返答する。各エージェントの返答がどのエージェントからのものかをユーザーが識別できなかった。具体的には：

- チャットバブルがすべて同じ見た目で、発言者が判別不能
- エージェント名がバブルに表示されない
- GemSelector チップの色がバブル色と連動していない
- 履歴（スレッド再ロード時）ではエージェント名がまったく表示されない

原因は複数層にわたっていた：

1. **バックエンド（メッセージ生成時）:** `SubAgent.run()` が `AIMessage` に `name=` を付与していなかったため、LangGraph チェックポイントにエージェント名が保存されなかった
2. **バックエンド（履歴取得時）:** `/api/threads/{id}/messages` の通常パスが `msg.name` を読んでも `senderName` フィールドに入れていなかった（debate パスは実装済みだったが通常パスは抜け落ちていた）
3. **フロントエンド（リアルタイム）:** `orchestrator_result` JSON の `agent_name` を `useChat.ts` でパースして `senderName` に変換する実装がなかった
4. **フロントエンド（表示）:** `MessageArea.tsx` に `senderName` に応じた色分け・バッジ表示のロジックがなかった

## Decision

エージェント識別を「名前→色」のハッシュ関数で一意に対応させる設計を採用した。

**バックエンド変更:**
- `SubAgent.run()`: `AIMessage(name=self.name, ...)` で常にエージェント名を付与
- `OrchestratorHandler`: ジョブ結果を `{"type":"orchestrator_result","content":"...","agent_name":"..."}` にラップ
- `/api/threads/{id}/messages` 通常パス: `getattr(msg, "name", None)` → `senderName` を設定（debate パスと統一）

**フロントエンド変更:**
- `utils/agentColor.ts` を新設: エージェント名の文字コードをハッシュしてパステルカラーを生成する `agentBgColor(name, isDark)` / `agentAccentColor(name)` を共有ユーティリティとして切り出し
- `MessageArea.tsx`: `senderName` があるバブルに `agentBgColor` の背景色を適用し、エージェント名をアクセントカラーのチップバッジとして表示
- `GemSelector.tsx`: 選択済みチップのボーダー・背景に `agentAccentColor(gem.name)` を使用し、バブル色と視覚的に一致させる

**ChatApp（通常チャット）との分離:**
- `APP.md` に `type: chat` フロントマターを追加し、`AppInfo.type` フィールドで ChatApp / SuperChatApp を分岐ルーティングするよう修正
- これにより `CanvasChatApp` が `appId:'canvas'` を持つようになり、通常チャットスレッドと混在しないよう修正

## Alternatives Considered

**固定色パレット（ラウンドロビン）:** エージェントを登録順で色に割り当てる案。スレッド内の登場順が変わると色が変わるため却下。

**エージェントに色を設定させる（DB管理）:** GEM ごとに色を DB に持たせる案。運用コストが高く、200名規模では不要と判断。ハッシュベースなら設定なしに安定した色が得られる。

**senderName をバブルテキストとして直接表示:** チップバッジにせず単なるテキストラベルとする案。当初の実装はこれだったが（`feat(superchat): show agent name`）、直後に `feat(ui): style agent name as chip badge` でバッジ化に変更。バッジの方が視覚的に「発言者ラベル」と明確に区別できる。

## Consequences

**ポジティブ:**
- エージェント名とカラーが新規メッセージ・履歴どちらでも一貫して表示される
- 色はエージェント名から決定論的に導出されるためスレッドを跨いで同一エージェントは同色になる
- `agentColor.ts` の一元管理により、今後 UI コンポーネントを追加しても色の不整合が起きにくい

**ネガティブ・注意点:**
- `AIMessage.name=` による `senderName` は今回の修正以降のメッセージのみ有効。それ以前の履歴は `name=None` のままで、バッジは表示されない（遡及修正は非現実的として見送り）
- `agentBgColor` のハッシュ衝突（異なるエージェント名が同色になる）は理論上あり得るが、200名・数十エージェント程度の規模では問題にならないと判断
- `GemSelector` のマルチセレクト化（`selectedGemId` → `selectedGemIds[]`）に伴い `OrchestratorHandler` の SQL が `ANY(::uuid[])` に変更された。古い単数形 `gem_id` パラメータとの後方互換性は `ac0d1e3` のワーカーシグネチャ修正で維持している
