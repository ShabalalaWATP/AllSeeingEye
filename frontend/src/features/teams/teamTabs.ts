export interface DashboardTab<Id extends string> {
  id: Id;
  label: string;
  detail: string;
}

export const tabId = (id: string) => `team-${id}-tab`;
export const panelId = (id: string) => `team-panel-${id}`;

/** Next index for a tablist key press, or null when the key is not a tab navigation key. */
export function nextTabIndex(key: string, current: number, count: number): number | null {
  if (key === 'ArrowRight') return (current + 1) % count;
  if (key === 'ArrowLeft') return (current - 1 + count) % count;
  if (key === 'Home') return 0;
  if (key === 'End') return count - 1;
  return null;
}
