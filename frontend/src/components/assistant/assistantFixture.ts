import { assistantAnswerSchema } from '@/lib/api/assistant';

export const eyeAnswer = assistantAnswerSchema.parse({
  paragraphs: [
    { kind: 'finding', text: 'Two recent vessel observations are available.', citations: ['E1'] },
    {
      kind: 'gap',
      text: 'AIS coverage is incomplete. Silence does not prove absence.',
      citations: [],
    },
  ],
  sources: [
    {
      id: 'E1',
      kind: 'event',
      record_id: 'vessel-1',
      source_id: 'aisstream',
      title: 'Example vessel position',
      url: 'https://example.org/vessel',
      published_at: null,
      observed_at: '2026-09-11T10:00:00Z',
      point: { lon: 179.5, lat: 42 },
      grade: 'F6',
    },
  ],
  scope: { mode: 'global', bbox: null, selected: null },
  coverage: {
    candidate_count: 42,
    matched_count: 8,
    selected_count: 2,
    source_count: 1,
    capped: true,
    notes: ['Only recent retained observations were searched.'],
  },
  generated_at: '2026-09-11T10:10:00Z',
  model: { name: 'fixture-model', reasoning_effort: 'high' },
});
