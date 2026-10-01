import type { LiveEvent } from '@/lib/api/eventSchemas';

/**
 * Language, optional script, optional region or UN M.49 area, then optional variants.
 * Deliberately narrower than full BCP 47 so arbitrary source strings never reach `lang`.
 */
const PLAUSIBLE_TAG =
  /^[a-z]{2,3}(?:-[a-z]{4})?(?:-(?:[a-z]{2}|\d{3}))?(?:-(?:[a-z\d]{5,8}|\d[a-z\d]{3}))*$/i;

/**
 * A canonical BCP 47 tag for a source-declared language, or `undefined` when the value is
 * undetermined (`und`), empty or not a plausible tag.
 */
export function sourceLanguageTag(language: string | null | undefined): string | undefined {
  const candidate = language?.trim().replaceAll('_', '-') ?? '';
  if (candidate.length > 35 || !PLAUSIBLE_TAG.test(candidate)) return undefined;
  if (/^und(?:-|$)/i.test(candidate)) return undefined;
  try {
    return Intl.getCanonicalLocales(candidate)[0];
  } catch {
    return undefined;
  }
}

type TitledEvent = Pick<LiveEvent, 'title' | 'title_en' | 'language'>;

/** The title to show, with the language it is written in (`null` for the English translation). */
export function shownTitle(event: TitledEvent): { text: string; language: string | null } {
  return event.title_en !== null
    ? { text: event.title_en, language: null }
    : { text: event.title, language: event.language };
}

/**
 * An English title for composing English labels, or `null` when only another-language (or
 * undetermined) original exists, so callers never mix an English prefix with foreign text.
 */
export function englishTitle(event: TitledEvent): string | null {
  if (event.title_en !== null) return event.title_en;
  return /^en(?:-|$)/.test(sourceLanguageTag(event.language) ?? '') ? event.title : null;
}
