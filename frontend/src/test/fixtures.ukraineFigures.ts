import type { CivilianHarm, ConfirmedLosses, LensSeries } from '@/lib/api/ukraine';
import type { UkraineFrontline, UkraineSpotted } from '@/lib/api/ukraineMap';

export const confirmedLosses: ConfirmedLosses = {
  recorded_on: '2026-09-12',
  retrieved_at: '2026-09-14T00:00:00Z',
  attribution: 'Oryx via the leedrake5 mirror (MIT).',
  licence: 'Mirror MIT; Oryx counts cited with attribution',
  source_url: 'https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-equipment.html',
  rows: [
    {
      side: 'ru',
      equipment_type: 'All Types',
      group: 'total',
      destroyed: 19034,
      damaged: 1000,
      abandoned: 1194,
      captured: 2838,
      total: 24066,
    },
    {
      side: 'ru',
      equipment_type: 'Tanks',
      group: 'tanks',
      destroyed: 3351,
      damaged: 165,
      abandoned: 392,
      captured: 538,
      total: 4446,
    },
    {
      side: 'ua',
      equipment_type: 'All Types',
      group: 'total',
      destroyed: 9507,
      damaged: 698,
      abandoned: 693,
      captured: 1199,
      total: 12097,
    },
  ],
  days: [
    { on: '2026-09-10', side: 'ru', total: 24000 },
    { on: '2026-09-10', side: 'ua', total: 12050 },
    { on: '2026-09-11', side: 'ru', total: 24030 },
    { on: '2026-09-11', side: 'ua', total: 12070 },
    { on: '2026-09-12', side: 'ru', total: 24066 },
    { on: '2026-09-12', side: 'ua', total: 12097 },
  ],
};

export const civilianHarm: CivilianHarm = {
  retrieved_at: '2026-09-14T00:00:00Z',
  source_url: 'https://ukraine.ohchr.org/en/reports/protection-of-civilians',
  attribution: 'UN Human Rights Monitoring Mission in Ukraine (HRMMU), OHCHR',
  months: [
    {
      month: '2026-07-01',
      title: 'Protection of Civilians in Armed Conflict — July 2026',
      url: 'https://ukraine.ohchr.org/en/Protection-of-Civilians-in-Armed-Conflict-July-2026',
      published_on: '2026-08-12',
      killed: 437,
      injured: 2610,
    },
    {
      month: '2026-03-01',
      title: 'Protection of Civilians in Armed Conflict — March 2026',
      url: 'https://ukraine.ohchr.org/en/Protection-of-Civilians-in-Armed-Conflict-March-2026',
      published_on: '2026-04-10',
      killed: null,
      injured: null,
    },
  ],
  references: [
    {
      id: 'mediazona-bbc-russian-dead',
      label: 'Mediazona and BBC News Russian: named Russian military dead',
      text: 'A running count confirmed one by one; a floor, not an estimate.',
      basis: 'documented',
      url: 'https://en.zona.media/article/2022/05/20/casualties_eng',
      as_of: '2026-06-30',
    },
    {
      id: 'kiel-support-tracker',
      label: 'Kiel Institute Ukraine Support Tracker',
      text: 'Aid committed and delivered by donor government.',
      basis: 'reported',
      url: 'https://www.ifw-kiel.de/topics/war-against-ukraine/ukraine-support-tracker/',
      as_of: '2026-06-30',
    },
  ],
};

const days = Array.from({ length: 14 }, (_, index) => {
  const day = new Date(Date.UTC(2026, 8, 13 - 13 + index));
  return day.toISOString().slice(0, 10);
});
const zeros = Array.from({ length: 14 }, () => 0);

export const lensSeries: LensSeries[] = (
  ['equipment', 'workforce', 'casualties', 'strikes', 'diplomacy'] as const
).map((lens) => ({
  lens,
  days,
  groups: {
    assessments: zeros,
    ukrainian: lens === 'workforce' ? [...zeros.slice(0, 13), 1] : zeros,
    russian: lens === 'equipment' ? [...zeros.slice(0, 13), 1] : zeros,
    international: zeros,
  },
}));

export const ukraineFrontlineOff: UkraineFrontline = {
  status: 'disabled',
  reason: 'No frontline provider is enabled.',
  provider: null,
  attribution: null,
  terms: null,
  assessed_at: null,
  downloaded_at: null,
  features: [],
};

export const ukraineFrontlineReady: UkraineFrontline = {
  status: 'ready',
  reason: 'Provider snapshot',
  provider: 'deepstate',
  attribution: 'DeepStateMap.live',
  terms: 'Shown with the DeepStateMap credit and link.',
  assessed_at: '12.09 o 21:04',
  downloaded_at: '2026-09-14T00:00:00Z',
  features: [
    {
      kind: 'occupied',
      label: 'Occupied',
      polygons: [
        [
          [
            [37.0, 48.0],
            [37.3, 48.0],
            [37.3, 48.3],
            [37.0, 48.0],
          ],
        ],
      ],
      lines: [],
    },
    {
      kind: 'line',
      label: 'Front line',
      polygons: [],
      lines: [
        [
          [36.9, 47.9],
          [37.4, 48.4],
        ],
      ],
    },
  ],
};

export const ukraineSpottedOff: UkraineSpotted = {
  status: 'disabled',
  reason: 'WarSpotting layer is off until the operator has read its terms.',
  attribution: 'WarSpotting',
  downloaded_at: null,
  losses: [],
};

export const ukraineSpottedReady: UkraineSpotted = {
  status: 'ready',
  reason: 'Provider snapshot',
  attribution: 'WarSpotting',
  downloaded_at: '2026-09-14T00:00:00Z',
  losses: [
    {
      id: 46987,
      lat: 48.122783,
      lon: 37.055325,
      model: "152mm 2S19(M1) 'Msta-S'",
      equipment_type: 'Self-propelled artillery',
      status: 'Destroyed',
      lost_by: 'Russia',
      on: '2026-09-10',
      place: 'Novoielyzavetivka, Pokrovsk raion',
    },
  ],
};
