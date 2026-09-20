import { expect, it } from 'vitest';
import { defaultProfile } from '@/test/handlers.profile';
import { initialDraft } from './researchRequest';
import { changeResearchFocus } from './researchTransitions';

it.each(['document', 'media'] as const)(
  'clears public scope and search when changing to private %s research',
  (focus) => {
    const draft = {
      ...initialDraft(defaultProfile, undefined, 'Question', null, 'UA'),
      inputId: 'old-input',
      subject: 'old subject',
      webSearch: true,
      conflictId: 'conflict',
      hazard: 'flood',
      history: { enabled: true, firstYear: '2000', lastYear: '2021' },
    };
    const result = changeResearchFocus(draft, focus);
    expect(result).toMatchObject({
      focus,
      subject: '',
      inputId: null,
      webSearch: false,
      countries: [],
      regions: [],
      conflictId: '',
      hazard: '',
      history: { enabled: false },
    });
    expect(result.question).toBe('Question');
    expect(draft.countries).toEqual(['UA']);
    expect(draft.history.enabled).toBe(true);
  },
);

it('retains public search for subject research and does not resurrect it after private research', () => {
  const draft = {
    ...initialDraft(defaultProfile, undefined, 'Question', null, 'UA'),
    webSearch: true,
  };
  expect(changeResearchFocus(draft, 'company')).toMatchObject({ webSearch: true, countries: [] });
  const privateDraft = changeResearchFocus(draft, 'document');
  expect(changeResearchFocus(privateDraft, 'general')).toMatchObject({
    webSearch: false,
    inputId: null,
  });
});
