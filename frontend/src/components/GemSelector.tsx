// frontend/src/components/GemSelector.tsx
// Chip UI for Gem selection in SuperChat (Phase 16).
// Green (#28a745) chips to visually distinguish from AgentSelector (blue #0366d6).
// Returns null if no Gems and not loading — no empty row shown.

import type { GemInfo } from '../types';

interface GemChipProps {
  gem: GemInfo;
  selected: boolean;
  onToggle: (gemId: string) => void;
}

function GemChip({ gem, selected, onToggle }: GemChipProps) {
  return (
    <button
      onClick={() => onToggle(gem.gem_id)}
      title={gem.description || gem.name}
      style={{
        padding: '4px 12px',
        borderRadius: '16px',
        border: `1px solid ${selected ? '#28a745' : '#d1dbe3'}`,
        background: selected ? '#28a745' : 'transparent',
        color: selected ? '#fff' : '#555',
        fontSize: '0.82rem',
        fontWeight: selected ? 600 : 400,
        cursor: 'pointer',
        transition: 'all 0.15s',
        whiteSpace: 'nowrap',
        flexShrink: 0,
      }}
    >
      {gem.name}
    </button>
  );
}

interface GemSelectorProps {
  gems: GemInfo[];
  selectedGemIds: string[];
  onToggle: (gemId: string) => void;
  isLoading: boolean;
}

export function GemSelector({ gems, selectedGemIds, onToggle, isLoading }: GemSelectorProps) {
  // Gem が1つもない場合は行を表示しない（D-13）
  if (!isLoading && gems.length === 0) return null;

  const selectedSet = new Set(selectedGemIds);
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '6px 12px',
        borderBottom: '1px solid #d1dbe3',
        background: '#f8f9fa',
        overflowX: 'auto',
        flexShrink: 0,
        minHeight: '38px',
      }}
    >
      <span
        style={{
          fontSize: '0.78rem',
          color: '#777',
          whiteSpace: 'nowrap',
          flexShrink: 0,
          marginRight: '4px',
        }}
      >
        Gems:
      </span>
      {isLoading ? (
        <span style={{ fontSize: '0.78rem', color: '#aaa' }}>Loading...</span>
      ) : (
        gems.map((gem) => (
          <GemChip
            key={gem.gem_id}
            gem={gem}
            selected={selectedSet.has(gem.gem_id)}
            onToggle={onToggle}
          />
        ))
      )}
    </div>
  );
}
