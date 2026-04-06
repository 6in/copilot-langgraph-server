// frontend/src/hooks/useGemSelector.ts
// Fetches available Gems from GET /api/gems and manages multi-selection state
// for SuperChat Gem invitation (Phase 16).
//
// Key differences from useGems (CRUD hook):
// - Default: ALL UNSELECTED (users explicitly invite Gems — opposite of useAgents)
// - toggleGem allows 0 selected (gem_ids=[] means "no Gem invited")
// - Read-only: no create/update/delete

import { useCallback, useEffect, useState } from 'react';
import { listGems } from '../api/client';
import type { GemInfo } from '../types';

interface UseGemSelectorReturn {
  gems: GemInfo[];
  selectedGemIds: string[];
  toggleGem: (gemId: string) => void;
  isLoading: boolean;
}

export function useGemSelector(): UseGemSelectorReturn {
  const [gems, setGems] = useState<GemInfo[]>([]);
  const [selectedGemIds, setSelectedGemIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    listGems()
      .then((data) => {
        if (cancelled) return;
        setGems(data);
        // デフォルト全未選択（ユーザーが明示的に招待する設計 — D-14）
      })
      .catch(() => {
        // Silently fail — gems list will be empty
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const toggleGem = useCallback((gemId: string) => {
    setSelectedGemIds((prev) => {
      const next = new Set(prev);
      if (next.has(gemId)) {
        next.delete(gemId);  // 0個選択も有効（Gem 招待なし）
      } else {
        next.add(gemId);
      }
      return next;
    });
  }, []);

  return {
    gems,
    selectedGemIds: Array.from(selectedGemIds),
    toggleGem,
    isLoading,
  };
}
