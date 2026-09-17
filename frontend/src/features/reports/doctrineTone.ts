import { PROBABILITY_TERMS } from '@/lib/doctrine';

/**
 * Colour in a report carries meaning, never decoration, and never on its own: every
 * tone below is rendered beside the label and the recorded value it describes.
 *
 * Nothing here interprets or re-grades. Each mapping is a display tone for a value the
 * saved report already states, and anything unrecognised falls back to a neutral tone
 * rather than being guessed at.
 */
export type Tone = 'strong' | 'mid' | 'caution' | 'neutral' | 'info';

/** Analytical confidence: how strong and stable the basis for a judgement is. */
export function confidenceTone(value: string | null | undefined): Tone {
  const term = value?.trim().toLowerCase();
  if (term === 'high') return 'strong';
  if (term === 'moderate') return 'mid';
  if (term === 'low') return 'caution';
  return 'neutral';
}

/**
 * Source reliability, A to F. F means there were insufficient grounds to judge, so it
 * is neutral: it is not a negative assessment of the source.
 */
export function reliabilityTone(value: string | null | undefined): Tone {
  const letter = value?.trim().toUpperCase().slice(0, 1);
  if (letter === 'A' || letter === 'B') return 'strong';
  if (letter === 'C') return 'mid';
  if (letter === 'D' || letter === 'E') return 'caution';
  return 'neutral';
}

/** Information credibility, 1 to 6. 6 means insufficient grounds to judge. */
export function credibilityTone(value: number | string | null | undefined): Tone {
  const number = typeof value === 'number' ? value : Number((value ?? '').trim());
  if (number === 1 || number === 2) return 'strong';
  if (number === 3) return 'mid';
  if (number === 4 || number === 5) return 'caution';
  return 'neutral';
}

/** An Admiralty grade such as "B2": a reliability letter and a credibility number. */
export function gradeTone(grade: string | null | undefined): Tone {
  const value = grade?.trim() ?? '';
  const letter = reliabilityTone(value.slice(0, 1));
  const number = credibilityTone(value.slice(1));
  if (letter === 'neutral' || number === 'neutral') return 'neutral';
  // The weaker half of the grade sets the tone; the text always shows both halves.
  if (letter === 'caution' || number === 'caution') return 'caution';
  if (letter === 'mid' || number === 'mid') return 'mid';
  return 'strong';
}

const PROBABILITY_ORDER = Object.keys(PROBABILITY_TERMS);

/**
 * Where a judgement sits on the UK PHIA yardstick, as a 1-based band index. The scale
 * is shown as a position, not as good or bad news: a low likelihood is not a warning.
 */
export function yardstickPosition(probability: string): { band: number; bands: number } {
  const index = PROBABILITY_ORDER.indexOf(probability);
  return { band: index < 0 ? 0 : index + 1, bands: PROBABILITY_ORDER.length };
}

/**
 * The recorded source flags, shown with their saved wording. Known viewpoint tags get
 * a caution or information tone; anything else stays neutral and literal.
 */
export function flagTone(flag: string): Tone {
  const value = flag.trim().toLowerCase();
  if (value === 'official') return 'info';
  if (value === 'state_controlled' || value === 'state_aligned' || value === 'participant')
    return 'caution';
  return 'neutral';
}

export function flagLabel(flag: string): string {
  return flag.replace(/_/g, ' ');
}
