// frontend/src/components/GemSelector.tsx
// Gem selection chip strip with inline create form and inline delete confirm.
// UI-SPEC Phase 15: chip strip above chat input bar.
// Restored in fix/ui-canvas-gem-issues: SuperChat GEM invitation feature.

import { useState } from 'react';
import { useGems } from '../hooks/useGems';
import { agentAccentColor } from '../utils/agentColor';

interface GemSelectorProps {
  selectedGemIds: string[];
  onToggleGem: (gemId: string) => void;
}

interface DeleteConfirmState {
  gemId: string;
}

export function GemSelector({ selectedGemIds, onToggleGem }: GemSelectorProps) {
  const { gems, isLoading, error, deleteGem } = useGems();
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirmState | null>(null);

  const handleDeleteConfirm = async (gemId: string) => {
    await deleteGem(gemId);
    setDeleteConfirm(null);
    if (selectedGemIds.includes(gemId)) {
      onToggleGem(gemId);
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

  const chipUnselected: React.CSSProperties = {
    ...chipBase,
    border: '1px solid #d1dbe3',
    background: 'transparent',
  };

  const chipSelectedFor = (name: string): React.CSSProperties => {
    const accent = agentAccentColor(name);
    return { ...chipBase, border: `2px solid ${accent}`, background: `${accent}1e` };
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
        {/* Gem chips */}
        {!isLoading && gems.map((gem) => {
          const isSelected = selectedGemIds.includes(gem.gem_id);
          const isConfirming = deleteConfirm?.gemId === gem.gem_id;

          return (
            <div
              key={gem.gem_id}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '2px', position: 'relative' }}
              className="gem-chip-wrapper"
            >
              <button
                style={isSelected ? chipSelectedFor(gem.name) : chipUnselected}
                aria-pressed={isSelected}
                onClick={() => onToggleGem(gem.gem_id)}
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

      </div>

      {/* Hover style for delete button */}
      <style>{`
        .gem-chip-wrapper:hover .gem-delete-btn {
          opacity: 1 !important;
        }
      `}</style>

      {/* Empty state */}
      {!isLoading && !error && gems.length === 0 && (
        <div style={{ padding: '4px 12px 8px', color: '#666', fontSize: '0.75rem' }}>
          No Gems yet. Create one from the Gems screen.
        </div>
      )}

      {/* Error state */}
      {error && (
        <div role="alert" style={{ padding: '4px 12px 8px', color: '#e05252', fontSize: '0.75rem' }}>
          {error}
        </div>
      )}
    </div>
  );
}
