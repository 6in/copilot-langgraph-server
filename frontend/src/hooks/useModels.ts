// frontend/src/hooks/useModels.ts
// Phase 36 D-16: GET /api/models fetch + 1h TTL in-memory キャッシュ。
// 単一モジュール変数 _cache で SPA 全体を通じて共有する (ユーザーごとに TTL リセット不要)。
//
// API 失敗時は models=null + error がセットされる。Header.tsx は null のとき
// fallback の MODEL_OPTIONS (ハードコード) で render するため、503 でも UI は壊れない。

import { useEffect, useState, useMemo, useCallback } from 'react';
import { getModels } from '../api/client';
import type { ModelInfo } from '../types';

let _cache: { at: number; models: ModelInfo[] } | null = null;
const TTL_MS = 60 * 60 * 1000; // 1h (D-16)

export function useModels() {
  const [models, setModels] = useState<ModelInfo[] | null>(
    _cache && Date.now() - _cache.at < TTL_MS ? _cache.models : null,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const now = Date.now();
    if (_cache && now - _cache.at < TTL_MS) {
      setModels(_cache.models);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    getModels()
      .then((list) => {
        if (cancelled) return;
        _cache = { at: now, models: list };
        setModels(list);
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setError(e);
        setModels(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const modelById = useCallback(
    (id: string): ModelInfo | undefined => {
      return (models ?? _cache?.models ?? []).find((m) => m.id === id);
    },
    [models],
  );

  const suggestedVisionModel = useMemo(() => {
    const list = models ?? _cache?.models ?? [];
    const pick = list.find((m) => m.vision);
    return pick?.id ?? null;
  }, [models]);

  return { models, isLoading, error, modelById, suggestedVisionModel };
}
