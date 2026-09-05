/** Display vocabulary for the doctrine enums the API returns. */
export const PROBABILITY_TERMS: Record<string, string> = {
  remote_chance: 'remote chance',
  highly_unlikely: 'highly unlikely',
  unlikely: 'unlikely',
  realistic_possibility: 'realistic possibility',
  likely: 'likely',
  highly_likely: 'highly likely',
  almost_certain: 'almost certain',
};

export function probabilityTerm(value: string): string {
  return PROBABILITY_TERMS[value] ?? value.replace(/_/g, ' ');
}

export const STATUS_LABELS: Record<string, string> = {
  ready: 'Ready',
  needs_review: 'Needs review',
  failed: 'Failed',
};
