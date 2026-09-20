import { convertLookback, lookbackForCadence } from './scheduleTimingPolicy';
import { expect, it } from 'vitest';
import { reportTemplates, schedule } from '@/test/fixtures';
import { evaluateSchedule, type ScheduleContext, type ScheduleDraft } from './scheduleDraft';

const draft: ScheduleDraft = {
  name: ' Weekly research ',
  template: 'ask',
  selectedCountries: ['UA'],
  regions: [],
  themes: [],
  question: ' What changed? ',
  notifyOnChange: true,
  researchMode: 'quick',
  languages: ' EN, fr, en, ',
  focus: 'general',
  subject: '',
  webSearch: true,
  sourceIds: null,
  hour: '6',
  cadence: 'weekly',
  weekday: '0',
  anchorMonth: '9',
  avoidRepetition: true,
  conflictId: 'conflict',
  hazard: 'flood',
  researchArea: null,
  discloseArea: false,
  monthday: '1',
  lookbackUnit: 'days',
  lookback: '7',
};
const context: ScheduleContext = {
  templates: reportTemplates,
  scope: { teamId: 'team', ready: true },
  selectedPlan: 'plan',
  invalidPlan: false,
};

it('normalises a valid research request and preserves explicit workspace, source and scope choices', () => {
  const result = evaluateSchedule(draft, context);
  expect(result.issues).toEqual([]);
  expect(result.request).toMatchObject({
    name: 'Weekly research',
    question: 'What changed?',
    team_id: 'team',
    plan_id: 'plan',
    research_languages: ['en', 'fr'],
    research_source_ids: null,
    country_iso: 'UA',
    country_isos: ['UA'],
    window_hours: 168,
    conflict_id: 'conflict',
    hazard: 'flood',
  });
  expect(draft.languages).toBe(' EN, fr, en, ');
});

it('subject research clears geographical and event scope from the payload', () => {
  const result = evaluateSchedule({ ...draft, focus: 'company', subject: ' Example ' }, context);
  expect(result.request).toMatchObject({
    country_isos: [],
    country_iso: null,
    regions: [],
    conflict_id: null,
    hazard: null,
    research_subject: 'Example',
    research_focus: 'company',
  });
});

it('area research excludes country and plan scope and requires disclosure unless paused', () => {
  const area = {
    geometry: {
      type: 'Polygon',
      coordinates: [
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 0],
        ],
      ],
    },
  };
  const areaDraft = { ...draft, researchArea: area };
  expect(evaluateSchedule(areaDraft, context).issues).toContainEqual({
    field: 'Area disclosure',
    message: 'Allow providers to receive the saved area.',
  });
  const result = evaluateSchedule({ ...areaDraft, discloseArea: true }, context);
  expect(result.invalid).toBe(false);
  expect(result.request).toMatchObject({
    research_area: area,
    disclose_area_to_provider: true,
    country_isos: [],
    conflict_id: null,
    hazard: null,
  });
  expect(result.request).not.toHaveProperty('plan_id');
  expect(
    evaluateSchedule(areaDraft, { ...context, initial: { ...schedule, enabled: false } }).invalid,
  ).toBe(false);
});

it('reports validation in field order while keeping unavailable workspaces and plans blocked', () => {
  const result = evaluateSchedule(
    { ...draft, name: '', question: '', languages: 'invalid!', lookback: '0' },
    { ...context, scope: { teamId: 'revoked', ready: false }, invalidPlan: true },
  );
  expect(result.issues.map((issue) => issue.field)).toEqual([
    'Subscription name',
    'Workspace',
    'Collection plan',
    'Question',
    'Research languages',
    'Search period',
  ]);
  expect(result.invalid).toBe(true);
});

it('omits research-only settings for standard products and preserves existing calendar settings', () => {
  const result = evaluateSchedule(
    { ...draft, template: 'intsum', lookbackUnit: 'default', languages: '' },
    {
      ...context,
      scope: { teamId: '', ready: true },
      initial: { ...schedule, timezone: 'Europe/London', local_minute: 30 },
    },
  );
  expect(result.invalid).toBe(false);
  expect(result.request).toMatchObject({
    window_hours: null,
    timezone: 'Europe/London',
    local_minute: 30,
    research_focus: 'general',
    research_web_search: false,
    notify_on_change: false,
    categories: [],
  });
  expect(result.request).not.toHaveProperty('research_languages');
  expect(result.request).not.toHaveProperty('team_id');
});

it('updates suggested lookback only while creating and retains deliberate lookback choices', () => {
  expect(lookbackForCadence('7', 'days', 'weekly', 'monthly', false)).toBe('31');
  expect(lookbackForCadence('7', 'days', 'weekly', 'monthly', true)).toBe('7');
  expect(lookbackForCadence('3', 'days', 'weekly', 'monthly', false)).toBe('3');
  expect(lookbackForCadence('7', 'hours', 'weekly', 'monthly', false)).toBe('7');
});

it('converts lookback units with whole-day rounding and a default seven-day interval', () => {
  expect(convertLookback('25', 'hours', 'days')).toBe('2');
  expect(convertLookback('2', 'days', 'hours')).toBe('48');
  expect(convertLookback('99', 'default', 'hours')).toBe('168');
  expect(convertLookback('99', 'default', 'days')).toBe('7');
  expect(convertLookback('2', 'days', 'default')).toBe('2');
});
