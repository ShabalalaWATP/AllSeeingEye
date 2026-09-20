import { isPrivateFocus, type ResearchDraft, type ResearchFocus } from './researchRequest';

/** Changing the research subject invalidates attached input and geographic scope. */
export function changeResearchFocus(draft: ResearchDraft, focus: ResearchFocus): ResearchDraft {
  return {
    ...draft,
    focus,
    subject: '',
    inputId: null,
    ...(isPrivateFocus(focus) ? { webSearch: false } : {}),
    ...(focus !== 'general'
      ? {
          countries: [],
          regions: [],
          conflictId: '',
          hazard: '',
          history: { ...draft.history, enabled: false },
        }
      : {}),
  };
}
