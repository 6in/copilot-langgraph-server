// frontend/src/components/GemsScreen.tsx
// Gems management hub screen: list, create, edit (inline), delete (inline confirm),
// and launch GemChatApp via onSelectGem callback.

import { useRef, useState } from 'react';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { useGems } from '../hooks/useGems';
import type { GemInfo } from '../types';

interface GemsScreenProps {
  onSelectGem: (gem: GemInfo) => void;
  onBack: () => void;
}

interface SkeletonCardProps {
  cardBg: string;
}

function SkeletonCard({ cardBg }: SkeletonCardProps) {
  return (
    <div
      style={{
        background: cardBg,
        borderRadius: '12px',
        padding: '24px',
        height: '120px',
        animation: 'pulse 0.8s ease-in-out infinite',
      }}
    >
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        button:focus-visible {
          outline: 2px solid #7c6ff7;
          outline-offset: 2px;
        }
      `}</style>
    </div>
  );
}

// Phase 40 Plan 01: 共有 Header の戻るボタンに統一したため画面内 Back を撤去。
// onBack は GemsScreenProps の型シグネチャ上は残るが (呼び出し元 App.tsx 互換性維持)、
// このコンポーネント内では使用しない。
export function GemsScreen({ onSelectGem }: GemsScreenProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const screenBg = isDark ? '#1e1e2e' : '#f5f5f5';
  const cardBg = isDark ? '#2a2a3e' : '#ffffff';
  const textColor = isDark ? '#e0e0e0' : '#333333';
  const cardBorder = isDark ? '#3a3a52' : '#dddddd';
  const subtitleColor = isDark ? '#a0a0b8' : '#666666';

  const { gems, isLoading, error, createGem, updateGem, deleteGem } = useGems();

  // Inline edit state
  const [editingGemId, setEditingGemId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editPrompt, setEditPrompt] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editKnowledge, setEditKnowledge] = useState('');
  const [editIsPublic, setEditIsPublic] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);

  // Inline delete confirmation state
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Create form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createPrompt, setCreatePrompt] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createKnowledge, setCreateKnowledge] = useState('');
  const [createType, setCreateType] = useState<'default' | 'canvas'>('default');
  const [createIsPublic, setCreateIsPublic] = useState(false);
  const [creating, setCreating] = useState(false);

  // Error state for form operations
  const [formError, setFormError] = useState<string | null>(null);

  // Incremental search filter
  const [filterText, setFilterText] = useState('');

  // Refs for autoFocus after form expansion
  const editNameRef = useRef<HTMLInputElement>(null);
  const createNameRef = useRef<HTMLInputElement>(null);

  const handleEdit = (gem: GemInfo) => {
    setEditingGemId(gem.gem_id);
    setEditName(gem.name);
    setEditPrompt(gem.system_prompt);
    setEditDescription(gem.description);
    setEditKnowledge(gem.knowledge);
    setEditIsPublic(gem.is_public);
    setConfirmDeleteId(null);
    setFormError(null);
    // autoFocus is handled via the autoFocus attribute on the input
  };

  const handleCancelEdit = () => {
    setEditingGemId(null);
    setEditName('');
    setEditPrompt('');
    setEditDescription('');
    setEditKnowledge('');
    setEditIsPublic(false);
  };

  const handleSave = async (gemId: string) => {
    setSavingId(gemId);
    setFormError(null);
    try {
      await updateGem(gemId, {
        name: editName,
        system_prompt: editPrompt,
        description: editDescription,
        knowledge: editKnowledge,
        is_public: editIsPublic,
      });
      setEditingGemId(null);
      setEditName('');
      setEditPrompt('');
      setEditDescription('');
      setEditKnowledge('');
      setEditIsPublic(false);
    } catch {
      setFormError('保存に失敗しました。もう一度お試しください。');
    } finally {
      setSavingId(null);
    }
  };

  const handleDeleteConfirm = (gemId: string) => {
    setConfirmDeleteId(gemId);
    setEditingGemId(null);
    setFormError(null);
  };

  const handleDelete = async (gemId: string) => {
    setDeletingId(gemId);
    setFormError(null);
    try {
      await deleteGem(gemId);
      setConfirmDeleteId(null);
    } catch {
      setFormError('削除に失敗しました。もう一度お試しください。');
    } finally {
      setDeletingId(null);
    }
  };

  const handleShowCreateForm = () => {
    setShowCreateForm(true);
    setCreateName('');
    setCreatePrompt('');
    setCreateDescription('');
    setCreateKnowledge('');
    setCreateType('default');
    setCreateIsPublic(false);
    setFormError(null);
  };

  const handleCancelCreate = () => {
    setShowCreateForm(false);
    setCreateName('');
    setCreatePrompt('');
    setCreateDescription('');
    setCreateKnowledge('');
    setCreateType('default');
    setCreateIsPublic(false);
  };

  const handleCreate = async () => {
    setCreating(true);
    setFormError(null);
    try {
      await createGem({
        name: createName,
        system_prompt: createPrompt,
        description: createDescription,
        knowledge: createKnowledge,
        type: createType,
        is_public: createIsPublic,
      });
      setShowCreateForm(false);
      setCreateName('');
      setCreatePrompt('');
      setCreateDescription('');
      setCreateKnowledge('');
      setCreateType('default');
      setCreateIsPublic(false);
    } catch {
      setFormError('Gem の作成に失敗しました。もう一度お試しください。');
    } finally {
      setCreating(false);
    }
  };

  const normalizedFilter = filterText.trim().toLowerCase();
  const filteredGems = normalizedFilter
    ? gems.filter(
        (g) =>
          g.name.toLowerCase().includes(normalizedFilter) ||
          g.description?.toLowerCase().includes(normalizedFilter)
      )
    : gems;

  const inputStyle: React.CSSProperties = {
    border: '1px solid #d1dbe3',
    borderRadius: '6px',
    padding: '8px 12px',
    fontSize: '0.875rem',
    width: '100%',
    boxSizing: 'border-box',
    background: cardBg,
    color: textColor,
  };

  const primaryBtnStyle: React.CSSProperties = {
    background: '#7c6ff7',
    color: '#fff',
    borderRadius: '6px',
    padding: '4px 12px',
    fontSize: '0.875rem',
    fontWeight: 600,
    border: 'none',
    cursor: 'pointer',
  };

  const secondaryBtnStyle: React.CSSProperties = {
    background: 'transparent',
    border: '1px solid #d1dbe3',
    borderRadius: '6px',
    padding: '4px 12px',
    fontSize: '0.875rem',
    color: textColor,
    cursor: 'pointer',
  };

  const destructiveBtnStyle: React.CSSProperties = {
    background: 'none',
    border: 'none',
    color: '#e05252',
    fontSize: '0.875rem',
    cursor: 'pointer',
    padding: '4px 8px',
  };

  const errorAlertStyle: React.CSSProperties = {
    background: 'rgba(224,82,82,0.1)',
    border: '1px solid #e05252',
    borderRadius: '8px',
    padding: '12px 16px',
    color: '#e05252',
    marginBottom: '16px',
  };

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '48px 32px',
        background: screenBg,
        overflowY: 'auto',
      }}
    >
      <style>{`
        button:focus-visible {
          outline: 2px solid #7c6ff7;
          outline-offset: 2px;
        }
      `}</style>

      <div style={{ maxWidth: '640px', width: '100%' }}>
        {/* ヘッダー行: 見出し "Gems" のみ (Back ボタンは共有 Header に統一 — Phase 40 Plan 01) */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            marginBottom: '16px',
          }}
        >
          <h1
            style={{
              fontSize: '2rem',
              fontWeight: 600,
              margin: 0,
              color: textColor,
            }}
          >
            Gems
          </h1>
        </div>

        {/* インクリメンタルサーチ */}
        <div style={{ position: 'relative', marginBottom: '24px' }}>
          <input
            type="search"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Gem を検索..."
            style={{
              width: '100%',
              boxSizing: 'border-box',
              padding: '8px 36px 8px 12px',
              border: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,
              borderRadius: '8px',
              background: isDark ? '#1e1e2e' : '#fff',
              color: textColor,
              fontSize: '0.875rem',
            }}
          />
          {filterText && (
            <button
              onClick={() => setFilterText('')}
              aria-label="検索をクリア"
              style={{
                position: 'absolute',
                right: '8px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: subtitleColor,
                fontSize: '1rem',
                lineHeight: 1,
                padding: '2px',
              }}
            >
              ✕
            </button>
          )}
        </div>

        {/* フェッチエラー */}
        {error && !isLoading && (
          <div role="alert" style={errorAlertStyle}>
            Gems の読み込みに失敗しました。ページを更新してください。
          </div>
        )}

        {/* フォームエラー */}
        {formError && (
          <div role="alert" style={errorAlertStyle}>
            {formError}
          </div>
        )}

        {/* ローディング: SkeletonCard x3 */}
        {isLoading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {[0, 1, 2].map((i) => (
              <SkeletonCard key={i} cardBg={cardBg} />
            ))}
          </div>
        )}

        {/* 空状態 */}
        {!isLoading && !error && filteredGems.length === 0 && !showCreateForm && (
          <div style={{ textAlign: 'center', padding: '48px 0' }}>
            <div style={{ fontWeight: 600, color: textColor, fontSize: '1rem' }}>
              Gems がありません
            </div>
            <div
              style={{
                fontSize: '0.85rem',
                color: subtitleColor,
                marginTop: '8px',
              }}
            >
              + ボタンをクリックして最初の Gem を作成してください
            </div>
          </div>
        )}

        {/* My Gems セクション */}
        {!isLoading && filteredGems.some((g) => g.is_owner) && (
          <div
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: subtitleColor,
              marginBottom: '12px',
            }}
          >
            My Gems
          </div>
        )}

        {!isLoading &&
          filteredGems.filter((g) => g.is_owner).map((gem) => (
            <div
              key={gem.gem_id}
              style={{
                background: cardBg,
                border: `1px solid ${cardBorder}`,
                borderRadius: '12px',
                padding: '24px',
                marginBottom: '16px',
              }}
            >
              {editingGemId === gem.gem_id ? (
                /* インライン編集フォーム */
                <div>
                  <div style={{ marginBottom: '12px' }}>
                    <label
                      style={{
                        display: 'block',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: textColor,
                        marginBottom: '4px',
                      }}
                    >
                      Name
                    </label>
                    <input
                      ref={editNameRef}
                      autoFocus
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      maxLength={80}
                      placeholder="e.g. Code Reviewer"
                      style={inputStyle}
                    />
                  </div>
                  <div style={{ marginBottom: '12px' }}>
                    <label
                      style={{
                        display: 'block',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: textColor,
                        marginBottom: '4px',
                      }}
                    >
                      System Prompt
                    </label>
                    <textarea
                      value={editPrompt}
                      onChange={(e) => setEditPrompt(e.target.value)}
                      maxLength={4000}
                      rows={4}
                      placeholder="このペルソナの役割・口調・制約を記述してください"
                      style={{ ...inputStyle, resize: 'vertical' }}
                    />
                  </div>
                  <div style={{ marginBottom: '12px' }}>
                    <label
                      style={{
                        display: 'block',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: textColor,
                        marginBottom: '4px',
                      }}
                    >
                      Description
                      <span style={{ fontWeight: 400, color: subtitleColor, marginLeft: '4px' }}>
                        （カード表示に使用）
                      </span>
                    </label>
                    <input
                      type="text"
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      maxLength={200}
                      placeholder="例: コードレビューを行う AI ペルソナ"
                      style={inputStyle}
                    />
                  </div>
                  <div style={{ marginBottom: '12px' }}>
                    <label
                      style={{
                        display: 'block',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: textColor,
                        marginBottom: '4px',
                      }}
                    >
                      Knowledge
                      <span style={{ fontWeight: 400, color: subtitleColor, marginLeft: '4px' }}>
                        （システムプロンプトに追加される知識）
                      </span>
                    </label>
                    <textarea
                      value={editKnowledge}
                      onChange={(e) => setEditKnowledge(e.target.value)}
                      maxLength={8000}
                      rows={3}
                      placeholder="ドメイン固有の知識・ルール・参照情報を記述してください"
                      style={{ ...inputStyle, resize: 'vertical' }}
                    />
                  </div>
                  <div style={{ marginBottom: '16px' }}>
                    <label
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: textColor,
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={editIsPublic}
                        onChange={(e) => setEditIsPublic(e.target.checked)}
                      />
                      全ユーザーに公開する
                      <span style={{ fontWeight: 400, color: subtitleColor }}>
                        （Shared Gems セクションに表示）
                      </span>
                    </label>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => handleSave(gem.gem_id)}
                      disabled={savingId === gem.gem_id}
                      style={{
                        ...primaryBtnStyle,
                        opacity: savingId === gem.gem_id ? 0.7 : 1,
                        cursor: savingId === gem.gem_id ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {savingId === gem.gem_id ? 'Saving...' : '変更を保存'}
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      disabled={savingId === gem.gem_id}
                      style={secondaryBtnStyle}
                    >
                      編集をやめる
                    </button>
                  </div>
                </div>
              ) : confirmDeleteId === gem.gem_id ? (
                /* インライン削除確認 */
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    flexWrap: 'wrap',
                  }}
                >
                  <span style={{ fontSize: '0.875rem', color: textColor }}>
                    削除しますか？
                  </span>
                  <button
                    onClick={() => handleDelete(gem.gem_id)}
                    disabled={deletingId === gem.gem_id}
                    style={{
                      ...destructiveBtnStyle,
                      fontWeight: 600,
                      opacity: deletingId === gem.gem_id ? 0.7 : 1,
                      cursor: deletingId === gem.gem_id ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {deletingId === gem.gem_id ? 'Deleting...' : 'Yes'}
                  </button>
                  <button
                    onClick={() => setConfirmDeleteId(null)}
                    disabled={deletingId === gem.gem_id}
                    style={secondaryBtnStyle}
                  >
                    No
                  </button>
                </div>
              ) : (
                /* 通常表示: Gem 名 + 説明 + アクションボタン */
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <div style={{ fontSize: '1rem', fontWeight: 600, color: textColor }}>
                      {gem.name}
                    </div>
                    {gem.is_public && (
                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          color: '#7c6ff7',
                          border: '1px solid #7c6ff7',
                          borderRadius: '4px',
                          padding: '1px 6px',
                        }}
                      >
                        公開中
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      fontSize: '0.875rem',
                      color: subtitleColor,
                      marginBottom: '16px',
                      lineHeight: 1.5,
                    }}
                  >
                    {gem.description
                      ? gem.description.slice(0, 80) + (gem.description.length > 80 ? '…' : '')
                      : <span style={{ fontStyle: 'italic', opacity: 0.6 }}>説明なし</span>
                    }
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <button onClick={() => onSelectGem(gem)} style={primaryBtnStyle}>
                      チャット開始
                    </button>
                    {gem.is_owner && (
                      <>
                        <button onClick={() => handleEdit(gem)} style={secondaryBtnStyle}>
                          Edit
                        </button>
                        <button onClick={() => handleDeleteConfirm(gem.gem_id)} style={destructiveBtnStyle}>
                          Delete
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

        {/* Shared Gems セクション */}
        {!isLoading && filteredGems.some((g) => !g.is_owner && g.is_public) && (
          <>
            <div
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: subtitleColor,
                marginTop: '8px',
                marginBottom: '12px',
              }}
            >
              Shared Gems
            </div>
            {filteredGems.filter((g) => !g.is_owner && g.is_public).map((gem) => (
              <div
                key={gem.gem_id}
                style={{
                  background: cardBg,
                  border: `1px solid ${cardBorder}`,
                  borderRadius: '12px',
                  padding: '24px',
                  marginBottom: '16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <div style={{ fontSize: '1rem', fontWeight: 600, color: textColor }}>
                    {gem.name}
                  </div>
                </div>
                <div
                  style={{
                    fontSize: '0.875rem',
                    color: subtitleColor,
                    marginBottom: '16px',
                    lineHeight: 1.5,
                  }}
                >
                  {gem.description
                    ? gem.description.slice(0, 80) + (gem.description.length > 80 ? '…' : '')
                    : <span style={{ fontStyle: 'italic', opacity: 0.6 }}>説明なし</span>
                  }
                </div>
                <button onClick={() => onSelectGem(gem)} style={primaryBtnStyle}>
                  チャット開始
                </button>
              </div>
            ))}
          </>
        )}

        {/* 新規作成フォーム */}
        {showCreateForm && (
          <div
            style={{
              background: cardBg,
              border: `1px solid ${cardBorder}`,
              borderRadius: '12px',
              padding: '24px',
              marginBottom: '16px',
            }}
          >
            <div
              style={{
                fontSize: '1rem',
                fontWeight: 600,
                color: textColor,
                marginBottom: '16px',
              }}
            >
              新しい Gem を作成
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: textColor,
                  marginBottom: '4px',
                }}
              >
                Name
              </label>
              <input
                ref={createNameRef}
                autoFocus
                type="text"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                maxLength={80}
                placeholder="e.g. Code Reviewer"
                style={inputStyle}
              />
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: textColor,
                  marginBottom: '4px',
                }}
              >
                System Prompt
              </label>
              <textarea
                value={createPrompt}
                onChange={(e) => setCreatePrompt(e.target.value)}
                maxLength={4000}
                rows={4}
                placeholder="このペルソナの役割・口調・制約を記述してください"
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: textColor,
                  marginBottom: '4px',
                }}
              >
                Description
                <span style={{ fontWeight: 400, color: subtitleColor, marginLeft: '4px' }}>
                  （カード表示に使用）
                </span>
              </label>
              <input
                type="text"
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                maxLength={200}
                placeholder="例: コードレビューを行う AI ペルソナ"
                style={inputStyle}
              />
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: textColor,
                  marginBottom: '4px',
                }}
              >
                Knowledge
                <span style={{ fontWeight: 400, color: subtitleColor, marginLeft: '4px' }}>
                  （システムプロンプトに追加される知識）
                </span>
              </label>
              <textarea
                value={createKnowledge}
                onChange={(e) => setCreateKnowledge(e.target.value)}
                maxLength={8000}
                rows={3}
                placeholder="ドメイン固有の知識・ルール・参照情報を記述してください"
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: textColor,
                  marginBottom: '4px',
                }}
              >
                Type
              </label>
              <select
                value={createType}
                onChange={(e) => setCreateType(e.target.value as 'default' | 'canvas')}
                style={inputStyle}
              >
                <option value="default">default</option>
                <option value="canvas">canvas</option>
              </select>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: textColor,
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={createIsPublic}
                  onChange={(e) => setCreateIsPublic(e.target.checked)}
                />
                全ユーザーに公開する
                <span style={{ fontWeight: 400, color: subtitleColor }}>
                  （Shared Gems セクションに表示）
                </span>
              </label>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={handleCreate}
                disabled={creating || !createName.trim()}
                style={{
                  ...primaryBtnStyle,
                  opacity: creating || !createName.trim() ? 0.7 : 1,
                  cursor: creating || !createName.trim() ? 'not-allowed' : 'pointer',
                }}
              >
                {creating ? 'Creating...' : 'Create Gem'}
              </button>
              <button
                onClick={handleCancelCreate}
                disabled={creating}
                style={secondaryBtnStyle}
              >
                キャンセル
              </button>
            </div>
          </div>
        )}

        {/* + New Gem ボタン（作成フォーム非表示時） */}
        {!showCreateForm && !isLoading && (
          <button
            onClick={handleShowCreateForm}
            style={{
              ...secondaryBtnStyle,
              padding: '8px 16px',
              fontSize: '0.875rem',
              marginTop: '8px',
            }}
          >
            + New Gem
          </button>
        )}
      </div>
    </div>
  );
}
