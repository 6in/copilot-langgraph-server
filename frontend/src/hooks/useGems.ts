// frontend/src/hooks/useGems.ts
// Gem CRUD state management hook.

import { useCallback, useEffect, useState } from 'react';
import { listGems, createGemApi, deleteGemApi } from '../api/client';
import type { GemInfo, GemCreate } from '../types';

interface UseGemsReturn {
  gems: GemInfo[];
  isLoading: boolean;
  error: string | null;
  createGem: (data: GemCreate) => Promise<GemInfo>;
  deleteGem: (gemId: string) => Promise<void>;
  refreshGems: () => Promise<void>;
}

export function useGems(): UseGemsReturn {
  const [gems, setGems] = useState<GemInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshGems = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await listGems();
      setGems(data);
    } catch {
      setError('Could not load Gems. Please refresh.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshGems();
  }, [refreshGems]);

  const createGem = useCallback(async (data: GemCreate): Promise<GemInfo> => {
    const gem = await createGemApi(data);
    setGems((prev) => [gem, ...prev]);
    return gem;
  }, []);

  const deleteGem = useCallback(async (gemId: string): Promise<void> => {
    await deleteGemApi(gemId);
    setGems((prev) => prev.filter((g) => g.gem_id !== gemId));
  }, []);

  return { gems, isLoading, error, createGem, deleteGem, refreshGems };
}
