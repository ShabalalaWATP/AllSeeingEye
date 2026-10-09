import { useDraftState } from '@/lib/formDrafts';

import type { ResearchFocus } from './researchRequest';

/**
 * Quick research shows the question, place and period; everything else keeps its saved
 * default. Advanced options reveal every step unchanged. Follow-ups, record or private-input
 * focus and project history need fields only the full form has, so they always show it.
 * Hiding the full form never clears a value already chosen there.
 */
export function useResearchFormMode({
  followUp,
  focus,
  historical,
  form = null,
}: {
  followUp: boolean;
  focus: ResearchFocus;
  historical: boolean;
  form?: string | null;
}) {
  const [expanded, setExpanded] = useDraftState(form, 'advanced', false);
  const required = followUp || focus !== 'general' || historical;
  return {
    advanced: expanded || required,
    /** True when the full form cannot be hidden for the current draft. */
    required,
    toggle: () => setExpanded((value) => !value),
    /** Show the full form, for example so a reader can reach a control an issue names. */
    open: () => setExpanded(true),
  };
}
