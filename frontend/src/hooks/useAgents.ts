// frontend/src/hooks/useAgents.ts
// Fetches available agents from GET /api/agents and manages selection state.
// All agents are selected by default after fetching.
// toggleAgent enforces minimum 1 agent selected.

import { useCallback, useEffect, useState } from 'react';
import { getAgents } from '../api/client';
import type { AgentInfo } from '../types';

interface UseAgentsReturn {
  agents: AgentInfo[];
  selectedAgents: string[];
  toggleAgent: (name: string) => void;
  isLoading: boolean;
}

export function useAgents(): UseAgentsReturn {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    getAgents()
      .then((data) => {
        if (cancelled) return;
        setAgents(data);
        // Select all agents by default
        setSelectedAgents(new Set(data.map((a) => a.name)));
      })
      .catch(() => {
        // Silently fail — agents list will be empty
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const toggleAgent = useCallback((name: string) => {
    setSelectedAgents((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        // Do not allow deselecting the last agent
        if (next.size <= 1) return prev;
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }, []);

  return {
    agents,
    selectedAgents: Array.from(selectedAgents),
    toggleAgent,
    isLoading,
  };
}
