/** Small parsers for the compact comma-separated fields the direction and warning forms use. */
import { CATEGORIES } from '@/lib/api/eventSchemas';
import type { Category } from '@/lib/api/eventSchemas';

/** Non-empty trimmed entries of a comma-separated field. */
export function parseCommaList(text: string): string[] {
  return text
    .split(',')
    .map((entry) => entry.trim())
    .filter((entry) => entry !== '');
}

/** ISO codes from a comma-separated field, upper-cased, two letters only. */
export function parseCountries(text: string): string[] {
  return parseCommaList(text)
    .map((code) => code.toUpperCase())
    .filter((code) => /^[A-Z]{2}$/.test(code));
}

/** Known categories from a comma-separated field; anything else is dropped. */
export function parseCategories(text: string): Category[] {
  return parseCommaList(text)
    .map((kind) => kind.toLowerCase())
    .filter((kind): kind is Category => (CATEGORIES as readonly string[]).includes(kind));
}
