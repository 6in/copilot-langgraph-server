# 0010. Gem 公開共有機能 — is_public フラグと Shared Gems セクション

**Date:** 2026-04-06  
**Status:** Accepted

## Context

Gem（AI ペルソナ）は当初、作成者（`github_login`）にのみ紐付いており、他ユーザーから参照できない設計だった。
社内 200 名規模での運用を想定すると、FAQ Bot やコードレビュー Bot など共通ペルソナを全ユーザーが利用できる仕組みが必要になった。

要件は以下の 3 点：

1. オーナーが任意の Gem をグローバルに公開できること
2. 公開 Gem は誰でも使えるが、編集・削除はオーナーのみ
3. UI で「自分の Gem」と「共有された Gem」を明確に区別できること

## Decision

**アプローチ C: `is_public` フラグ + `is_owner` フィールドによるサーバーサイド所有者判定を採用。**

- `gems` テーブルに `is_public BOOLEAN NOT NULL DEFAULT false` カラムを追加（`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` で idempotent に適用）
- `list_gems` / `get_gem` の WHERE 句を `github_login = %s OR is_public = true` に変更し、公開 Gem を全ユーザーへ返す
- `GemInfo` レスポンスに `is_public` と `is_owner`（`github_login == current_login` で算出）を含める
- `update_gem` / `delete_gem` は引き続き `WHERE gem_id = %s AND github_login = %s` — 所有者のみ変更可
- フロントエンドは `is_owner` フラグで Edit/Delete ボタンの表示を制御し、GemsScreen を「My Gems」と「Shared Gems」の 2 セクションに分割
- 作成・編集フォームに「全ユーザーに公開する」チェックボックスを追加

## Alternatives Considered

**アプローチ A: ロールベース管理（admin が公開 Gem を管理）**  
管理者 UI と権限テーブルが必要で実装コストが高い。200 名規模では過剰。却下。

**アプローチ B: グループ・チーム単位の共有**  
GitHub Teams API との連携が必要で、Copilot SDK の Technical Preview 制約と相性が悪い。今後の拡張候補として保留。

**フロントエンドで所有者を判定する案**  
JWT の `github_login` をフロントエンドで保持して比較する方法も検討したが、サーバーサイドで `is_owner` を計算してレスポンスに含める方が一貫性が高く、フロントが認証情報を別途管理する必要がなくなるため採用。

## Consequences

**ポジティブ:**
- 共通ペルソナ（FAQ Bot 等）を管理者が作成・公開し、全ユーザーが使える運用フローが成立する
- `is_owner` フラグをサーバーが返すため、フロントは「誰が使っているか」を意識せずに権限制御できる
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` による idempotent な migration で既存 Gem データに影響なし

**ネガティブ・注意点:**
- 公開 Gem の `system_prompt` と `knowledge` は読み取り専用だが、API レスポンスとして全文が返る。機密性の高い情報は公開 Gem に含めないよう運用ルールで補完が必要
- `list_gems` の ORDER BY は `(github_login = %s) DESC, created_at DESC`（自分の Gem を先頭に、次に他者の公開 Gem）。PostgreSQL でブール値を ORDER BY する際は `true > false` の降順が期待通りに動く
- 将来グループ共有に拡張する場合は、`is_public` フラグと並行して `gem_permissions` テーブルを追加するパスが自然（既存フラグとの後方互換を維持しやすい）
