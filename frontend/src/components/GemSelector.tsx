// frontend/src/components/GemSelector.tsx
// Gem selection chip strip with inline create form and inline delete confirm.
// UI-SPEC Phase 15: chip strip above chat input bar.

import { useState } from 'react';
import { useGems } from '../hooks/useGems';
import type { GemCreate } from '../types';

interface GemSelectorProps {
  selectedGemId: string | null;
  onSelectGem: (gemId: string | null) => void;
}

interface DeleteConfirmState {
  gemId: string;
}

export function GemSelector({ selectedGemId, onSelectGem }: GemSelectorProps) {
  const { gems, isLoading, error, createGem, deleteGem } = useGems();
  const [showForm, setShowForm] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirmState | null>(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formPrompt, setFormPrompt] = useState('');
  const [formType, setFormType] = useState<'default' | 'canvas'>('default');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async () => {
    if (!formName.trim()) return;
    setIsCreating(true);
    try {
      const data: GemCreate = { name: formName.trim(), system_prompt: formPrompt, type: formType };
      await createGem(data);
      setFormName('');
      setFormPrompt('');
      setFormType('default');
      setShowForm(false);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteConfirm = async (gemId: string) => {
    await deleteGem(gemId);
    setDeleteConfirm(null);
    if (selectedGemId === gemId) {
      onSelectGem(null);
    }
  };

  const chipBase: React.CSSProperties = {
    borderRadius: '14px',
    height: '28px',
    padding: '0 12px',
    fontSize: '0.875rem',
    fontWeight: 600,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    flexShrink: 0,
    transition: 'opacity 0.1s',
  };

  const chipSelected: React.CSSProperties = {
    ...chipBase,
    border: '2px solid #7c6ff7',
    background: 'rgba(124,111,247,0.12)',
  };

  const chipUnselected: React.CSSProperties = {
    ...chipBase,
    border: '1px solid #d1dbe3',
    background: 'transparent',
  };

  const focusVisibleStyle = `
    button:focus-visible {
      outline: 2px solid #7c6ff7;
      outline-offset: 2px;
    }
  `;

  const truncate = (text: string, max: number) =>
    text.length > max ? text.slice(0, max) + '...' : text;

  return (
    <div style={{ borderBottom: '1px solid #d1dbe3', background: '#fff' }}>
      <style>{focusVisibleStyle}</style>

      {/* Chip strip */}
      <div
        style={{
          display: 'flex',
          overflowX: 'auto',
          gap: '8px',
          padding: '4px 12px',
          alignItems: 'center',
        }}
        role="group"
        aria-label="Gem selection"
      >
        {/* No Gem chip */}
        <button
          style={selectedGemId === null ? chipSelected : chipUnselected}
          aria-pressed={selectedGemId === null}
          onClick={() => onSelectGem(null)}
        >
          No Gem
        </button>

        {/* Gem chips */}
        {!isLoading && gems.map((gem) => {
          const isSelected = selectedGemId === gem.gem_id;
          const isConfirming = deleteConfirm?.gemId === gem.gem_id;

          return (
            <div
              key={gem.gem_id}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '2px', position: 'relative' }}
              className="gem-chip-wrapper"
            >
              <button
                style={isSelected ? chipSelected : chipUnselected}
                aria-pressed={isSelected}
                onClick={() => onSelectGem(gem.gem_id)}
                title={gem.name}
              >
                {truncate(gem.name, 20)}
              </button>

              {isConfirming ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}>
                  <span style={{ color: '#333' }}>Delete?</span>
                  <button
                    onClick={() => handleDeleteConfirm(gem.gem_id)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#e05252', fontWeight: 600, padding: '0 2px', fontSize: '0.75rem' }}
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#666', padding: '0 2px', fontSize: '0.75rem' }}
                  >
                    No
                  </button>
                </span>
              ) : (
                <button
                  aria-label="Gem を削除"
                  onClick={() => setDeleteConfirm({ gemId: gem.gem_id })}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#e05252',
                    padding: '0 2px',
                    fontSize: '0.75rem',
                    opacity: 0,
                    transition: 'opacity 0.15s',
                    lineHeight: 1,
                  }}
                  className="gem-delete-btn"
                >
                  x
                </button>
              )}
            </div>
          );
        })}

        {/* + chip */}
        <button
          style={chipUnselected}
          aria-label="Create new Gem"
          onClick={() => setShowForm((v) => !v)}
        >
          +
        </button>
      </div>

      {/* Hover style for delete button */}
      <style>{`
        .gem-chip-wrapper:hover .gem-delete-btn {
          opacity: 1 !important;
        }
      `}</style>

      {/* Empty state */}
      {!isLoading && !error && gems.length === 0 && !showForm && (
        <div style={{ padding: '4px 12px 8px', color: '#666', fontSize: '0.75rem' }}>
          No Gems yet. Click + to create one.
        </div>
      )}

      {/* Error state */}
      {error && (
        <div role="alert" style={{ padding: '4px 12px 8px', color: '#e05252', fontSize: '0.75rem' }}>
          {error}
        </div>
      )}

      {/* Inline create form */}
      <div style={{ display: showForm ? 'block' : 'none', padding: '0 12px 12px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '480px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label htmlFor="gem-name" style={{ fontSize: '0.875rem', fontWeight: 600, color: '#333' }}>
              Name
            </label>
            <input
              id="gem-name"
              type="text"
              maxLength={80}
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="e.g. Code Reviewer"
              style={{
                border: '1px solid #d1dbe3',
                borderRadius: '6px',
                padding: '6px 10px',
                fontSize: '0.875rem',
                outline: 'none',
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label htmlFor="gem-prompt" style={{ fontSize: '0.875rem', fontWeight: 600, color: '#333' }}>
              System Prompt
            </label>
            <textarea
              id="gem-prompt"
              rows={4}
              maxLength={4000}
              value={formPrompt}
              onChange={(e) => setFormPrompt(e.target.value)}
              placeholder="You are a helpful assistant specialized in..."
              style={{
                border: '1px solid #d1dbe3',
                borderRadius: '6px',
                padding: '6px 10px',
                fontSize: '0.875rem',
                fontFamily: 'inherit',
                resize: 'vertical',
                outline: 'none',
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#333' }}>Type</span>
            <div style={{ display: 'flex', gap: '16px' }}>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="gem-type"
                  value="default"
                  checked={formType === 'default'}
                  onChange={() => setFormType('default')}
                />
                Chat
              </label>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="gem-type"
                  value="canvas"
                  checked={formType === 'canvas'}
                  onChange={() => setFormType('canvas')}
                />
                Canvas
              </label>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleCreate}
              disabled={isCreating || !formName.trim()}
              style={{
                background: '#7c6ff7',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                height: '36px',
                padding: '0 16px',
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: isCreating || !formName.trim() ? 'not-allowed' : 'pointer',
                opacity: isCreating || !formName.trim() ? 0.6 : 1,
              }}
            >
              {isCreating ? 'Creating...' : 'Create Gem'}
            </button>
            <button
              onClick={() => {
                setShowForm(false);
                setFormName('');
                setFormPrompt('');
                setFormType('default');
              }}
              style={{
                background: 'none',
                border: '1px solid #d1dbe3',
                borderRadius: '6px',
                height: '36px',
                padding: '0 16px',
                fontSize: '0.875rem',
                cursor: 'pointer',
                color: '#333',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
