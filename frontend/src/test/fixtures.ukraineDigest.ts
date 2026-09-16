import type { UkraineDigestEntry, UkraineDigestView } from '@/lib/api/ukraineDigest';

export const ukraineDigestEntry: UkraineDigestEntry = {
  period_start: '2026-09-02',
  period_end: '2026-09-16',
  generated_at: '2026-09-16T06:30:00Z',
  model: 'fixture-assessment-model',
  evidence_items: 28,
  source_ids: ['isw_assessments', 'kyiv_independent', 'meduza_en', 'ukraine_general_staff'],
  prompt_tokens: 9_400,
  completion_tokens: 1_100,
  battlefield: {
    summary:
      'Reporting suggests the fortnight brought little confirmed change on the ground. ' +
      'Assessments describe continued pressure in the east and repeated strikes on energy sites.',
    changes: [
      {
        text: 'Assessments describe continued Russian attacks near the eastern city, with advances described as marginal.',
        source_ids: ['e1', 'e2'],
      },
      {
        text: 'Regional authorities reported damage to energy substations overnight, according to Ukrainian reporting.',
        source_ids: ['e3'],
      },
      {
        text:
          'The General Staff of Ukraine claimed further Russian equipment losses. ' +
          'These are one side’s claims, not verified counts.',
        source_ids: ['e8'],
      },
    ],
  },
  political: {
    summary:
      'Political reporting centred on further funding for Ukraine, with positions restated ' +
      'rather than settled.',
    changes: [
      {
        text: 'European ministers met to discuss further funding, with no final decision reported.',
        source_ids: ['e6'],
      },
      {
        text: 'Russian officials repeated existing positions on talks, according to state reporting.',
        source_ids: ['e7'],
      },
    ],
  },
  watch: [
    'Whether reported strikes on energy infrastructure continue into winter.',
    'Whether the discussed funding turns into a stated decision.',
  ],
  caveats: [
    'This digest reads only the sources listed and cannot verify any of them.',
    'Claims by either government are recorded as claims, never as established facts.',
  ],
  citations: [
    {
      id: 'e1',
      kind: 'assessment',
      source_id: 'isw_assessments',
      label: 'Russian offensive campaign assessment',
      dated_on: '2026-09-15',
      url: 'https://understandingwar.org/example',
    },
    {
      id: 'e2',
      kind: 'assessment',
      source_id: 'isw_assessments',
      label: 'Russian offensive campaign assessment, later',
      dated_on: '2026-09-13',
      url: null,
    },
    {
      id: 'e3',
      kind: 'battlefield',
      source_id: 'kyiv_independent',
      label: 'Strikes reported on energy infrastructure',
      dated_on: '2026-09-15',
      url: 'https://kyivindependent.example/strikes',
    },
    {
      id: 'e6',
      kind: 'political',
      source_id: 'kyiv_independent',
      label: 'European ministers discussed further support',
      dated_on: '2026-09-14',
      url: 'https://kyivindependent.example/ministers',
    },
    {
      id: 'e7',
      kind: 'political',
      source_id: 'meduza_en',
      label: 'Russian officials commented on talks',
      dated_on: '2026-09-10',
      url: 'https://meduza.example/talks',
    },
    {
      id: 'e8',
      kind: 'claim',
      source_id: 'ukraine_general_staff',
      label: 'General Staff of Ukraine claimed Russian losses, day 1301',
      dated_on: '2026-09-15',
      url: 'https://example.invalid/claim',
    },
  ],
};

export const ukraineDigestPrevious: UkraineDigestEntry = {
  ...ukraineDigestEntry,
  period_start: '2026-08-19',
  period_end: '2026-09-02',
  generated_at: '2026-09-02T06:30:00Z',
  battlefield: {
    summary: 'The previous fortnight showed little verifiable change on the ground.',
    changes: ukraineDigestEntry.battlefield.changes.slice(0, 2),
  },
};

export const ukraineDigest: UkraineDigestView = {
  status: 'ready',
  reason: null,
  stale: false,
  generating: false,
  interval_days: 14,
  latest: ukraineDigestEntry,
  previous: [ukraineDigestPrevious],
};

export const ukraineDigestNone: UkraineDigestView = {
  status: 'none',
  reason: null,
  stale: false,
  generating: false,
  interval_days: 14,
  latest: null,
  previous: [],
};

export const ukraineDigestGenerating: UkraineDigestView = {
  ...ukraineDigestNone,
  status: 'generating',
  generating: true,
};

export const ukraineDigestUnavailable: UkraineDigestView = {
  ...ukraineDigestNone,
  status: 'unavailable',
  reason: 'No model is assigned, so no digest can be written.',
};

export const ukraineDigestRejected: UkraineDigestView = {
  ...ukraineDigestNone,
  status: 'validation_failed',
  reason:
    'The model answer did not pass the checks this application runs before storing a digest, ' +
    'so nothing was saved.',
};

export const ukraineDigestStale: UkraineDigestView = {
  ...ukraineDigest,
  stale: true,
  previous: [],
};
