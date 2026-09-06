/** Turning the compact plan form text into requirement objects. */
import type { SirRequest } from '@/lib/api/direction';
import { parseCategories, parseCommaList, parseCountries } from '@/lib/text';

export { parseCountries };

/** "text | keyword, keyword | category, category" per line; blank lines are skipped. */
export function parseSirLines(text: string): SirRequest[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '')
    .map((line) => {
      const [sirText = '', keywords = '', categories = ''] = line.split('|').map((p) => p.trim());
      const request: SirRequest = { text: sirText };
      const words = parseCommaList(keywords);
      if (words.length > 0) request.keywords = words;
      const kinds = parseCategories(categories);
      if (kinds.length > 0) request.categories = kinds;
      return request;
    })
    .filter((sir) => sir.text !== '');
}

/** "west, south, east, north" in degrees; null unless all four numbers are present. */
export function parseBox(text: string): [number, number, number, number] | null {
  const parts = text.split(',').map((part) => Number(part.trim()));
  const [west, south, east, north] = parts;
  if (parts.length !== 4 || west === undefined || south === undefined) return null;
  if (east === undefined || north === undefined) return null;
  if (![west, south, east, north].every(Number.isFinite)) return null;
  return [west, south, east, north];
}
