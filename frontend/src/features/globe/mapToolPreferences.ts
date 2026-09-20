import { mapPanelId, resolveMapPanel } from '@/lib/mapLayerDirectory';

const KEY = 'ase.map.tool-favourites';

/** Only public tool identifiers are stored here, never map objects or study data. */
export function readToolFavourites(): string[] | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw === null || raw.length > 1024) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length > 4) return null;
    const ids: string[] = [];
    for (const value of parsed) {
      if (typeof value !== 'string') return null;
      const label = resolveMapPanel(value);
      const id = label === null ? null : mapPanelId(label);
      if (id === null || ids.includes(id)) return null;
      ids.push(id);
    }
    return ids;
  } catch {
    return null;
  }
}

export function writeToolFavourites(ids: string[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(ids));
  } catch {
    /* Restricted browser storage must not prevent using a tool. */
  }
}
