/** Areas of interest and collection plans with evidence gathered against them. */
import type { AreaOfInterest, CollectionPlan, PlanEvidence } from '@/lib/api/direction';

import { liveEvent } from './fixtures.events';

export const aoi: AreaOfInterest = {
  team_id: null,
  id: 'a1a1a1a1-a1a1-4a1a-8a1a-a1a1a1a1a1a1',
  name: 'Eastern Ukraine',
  description: '',
  kind: 'bbox',
  bbox: [30, 44, 41, 53],
  countries: [],
  created_by: '22222222-2222-4222-8222-222222222222',
  created_at: '2026-09-04T10:00:00Z',
};

export const plan: CollectionPlan = {
  team_id: null,
  id: 'b2b2b2b2-b2b2-4b2b-8b2b-b2b2b2b2b2b2',
  name: 'Kharkiv axis',
  description: 'Background from the curated tracker.',
  aoi_id: aoi.id,
  countries: ['UA'],
  pirs: [
    {
      code: 'PIR-1',
      text: 'Will Russia mount a new offensive towards Kharkiv?',
      sirs: [
        {
          code: 'SIR-1.1',
          text: 'Strikes and shelling around Kharkiv',
          keywords: ['Kharkiv', 'shelling'],
          categories: [],
        },
        {
          code: 'SIR-1.2',
          text: 'Talks or ceasefire moves',
          keywords: ['talks'],
          categories: ['news'],
        },
      ],
    },
  ],
  enabled: true,
  created_by: '22222222-2222-4222-8222-222222222222',
  created_at: '2026-09-04T10:05:00Z',
  updated_at: '2026-09-04T10:05:00Z',
};

export const planEvidence: PlanEvidence = {
  plan,
  aoi,
  considered: 12,
  sirs: [
    {
      code: 'SIR-1.1',
      text: 'Strikes and shelling around Kharkiv',
      events: [
        liveEvent({
          id: 'k1',
          category: 'conflict',
          title: 'Shelling in Kharkiv',
          point: { lon: 36.2, lat: 49.9 },
          country_iso: 'UA',
        }),
      ],
    },
    { code: 'SIR-1.2', text: 'Talks or ceasefire moves', events: [] },
  ],
};
