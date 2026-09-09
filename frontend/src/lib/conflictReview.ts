import type { LiveEvent } from './api/eventSchemas';

type ReviewEvent = Pick<LiveEvent, 'category' | 'source_id' | 'tags' | 'attributes'>;
export type ConflictRelevance =
  'armed_conflict' | 'civil_unrest' | 'military_activity' | 'context' | 'unrelated' | 'uncertain';

const LABELS: Record<ConflictRelevance, string> = {
  armed_conflict: 'Armed conflict reporting',
  civil_unrest: 'Civil unrest reporting',
  military_activity: 'Military activity reporting',
  context: 'Context reporting',
  unrelated: 'Unrelated to conflict',
  uncertain: 'Uncertain media signal',
};

export interface ConflictReview {
  state: 'pending' | 'accepted' | 'uncertain' | 'excluded';
  relevance: ConflictRelevance | null;
  label: string;
  assessed: boolean;
  reason: string | null;
  quote: string | null;
  model: string | null;
  source: string | null;
}

function text(event: ReviewEvent, key: string): string | null {
  const value = event.attributes[key];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

/** Relevance screening never establishes accuracy, source independence or exact geography. */
export function conflictReview(event: ReviewEvent): ConflictReview | null {
  const assessed = event.attributes.conflict_screening === 'llm';
  if (
    event.category !== 'conflict' ||
    (!assessed && event.source_id !== 'gdelt_events' && !event.tags.includes('machine_coded'))
  )
    return null;
  const raw = text(event, 'conflict_relevance');
  const relevance = raw && Object.hasOwn(LABELS, raw) ? (raw as ConflictRelevance) : null;
  const excluded = relevance === 'context' || relevance === 'unrelated';
  const state = excluded
    ? 'excluded'
    : !assessed || relevance === null
      ? 'pending'
      : relevance === 'uncertain'
        ? 'uncertain'
        : 'accepted';
  return {
    state,
    relevance,
    label:
      state === 'pending' || relevance === null ? 'Unreviewed media signal' : LABELS[relevance],
    assessed,
    reason: text(event, 'conflict_screening_reason'),
    quote: text(event, 'conflict_screening_quote'),
    model: text(event, 'conflict_screening_model'),
    source: text(event, 'conflict_screening_source'),
  };
}

export function isUnreviewedConflictSignal(event: ReviewEvent): boolean {
  const review = conflictReview(event);
  return review?.state === 'pending' || review?.state === 'uncertain';
}

export function matchesConflictReview(event: ReviewEvent, includeUnreviewed = false): boolean {
  const review = conflictReview(event);
  return (
    review === null ||
    review.state === 'accepted' ||
    (includeUnreviewed && (review.state === 'pending' || review.state === 'uncertain'))
  );
}
