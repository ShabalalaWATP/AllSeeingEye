/** Turning the compact plan form text into requirement objects. */
import { CATEGORIES } from '@/lib/api/eventSchemas';
import type { Category } from '@/lib/api/eventSchemas';
import type { SirRequest } from '@/lib/api/direction';

/** "text | keyword, keyword | category, category" per line; blank lines are skipped. */
export function parseSirLines(text: string): SirRequest[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '')
    .map((line) => {
      const [sirText = '', keywords = '', categories = ''] = line.split('|').map((p) => p.trim());
      const request: SirRequest = { text: sirText };
      const words = keywords
        .split(',')
        .map((word) => word.trim())
        .filter((word) => word !== '');
      if (words.length > 0) request.keywords = words;
      const kinds = categories
        .split(',')
        .map((kind) => kind.trim().toLowerCase())
        .filter((kind): kind is Category => (CATEGORIES as readonly string[]).includes(kind));
      if (kinds.length > 0) request.categories = kinds;
      return request;
    })
    .filter((sir) => sir.text !== '');
}

/** ISO codes from a comma-separated field, upper-cased, two letters only. */
export function parseCountries(text: string): string[] {
  return text
    .split(',')
    .map((code) => code.trim().toUpperCase())
    .filter((code) => /^[A-Z]{2}$/.test(code));
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
