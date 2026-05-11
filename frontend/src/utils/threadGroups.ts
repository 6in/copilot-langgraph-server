// frontend/src/utils/threadGroups.ts
// Date-based grouping of threads — extracted from ThreadSidebar.tsx during Phase 35 (D-02).
// Shared by ThreadSidebar (existing consumer) and MenuScreen "最近のスレッド" section (Plan 06).

import type { ThreadInfo } from '../types';

export type DateGroup = '今日' | '昨日' | '今週' | '先週' | 'それ以前';

export const groupOrder: DateGroup[] = ['今日', '昨日', '今週', '先週', 'それ以前'];

export function getDateGroup(updatedAt?: string | null): DateGroup {
  if (!updatedAt) return 'それ以前';
  const now = new Date();
  const updated = new Date(updatedAt);
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffMs =
    todayStart.getTime() -
    new Date(updated.getFullYear(), updated.getMonth(), updated.getDate()).getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 0 || diffDays === 0) return '今日';
  if (diffDays === 1) return '昨日';
  if (diffDays <= 7) return '今週';
  if (diffDays <= 14) return '先週';
  return 'それ以前';
}

export function groupThreads(threads: ThreadInfo[]): Map<DateGroup, ThreadInfo[]> {
  const groups = new Map<DateGroup, ThreadInfo[]>();
  for (const thread of threads) {
    const group = getDateGroup(thread.updated_at);
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(thread);
  }
  return groups;
}
