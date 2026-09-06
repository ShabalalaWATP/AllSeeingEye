import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import { researchReceiptSchema } from '@/lib/api/reportResearch';
import { planSchema, previewSchema } from '@/lib/api/researchPlan';
import { researchReceipt } from '@/test/fixtures.researchMetadata';
import { SavedCollectionPlan } from './SavedCollectionPlan';

const frozenPlan = {
  question: 'A question',
  since: '2026-01-01T00:00:00Z',
  until: '2026-01-02T00:00:00Z',
  languages: ['fa'],
  mode: 'quick',
  focus: 'general',
  subject: null,
  country_iso: 'IR',
  tasks: [
    {
      source_id: 'example',
      source_name: 'Example record source',
      selected: true,
      supported: true,
      language: 'fa',
      terms: ['بندر'],
      provenance: 'operator_supplied_variant',
      temporal_scope: 'requested_window',
    },
  ],
  request_limit: 8,
  seconds_limit: 20,
  item_limit: 50,
  policy_version: 'v1',
  model_calls: 0,
  translation_calls: 0,
  replans: 0,
};
const translation = {
  policy_version: 'query-translation-v1',
  original_terms: ['Port ABC-123'],
  languages: ['fa', 'zh-Hant'],
  model: 'configured-model',
  status: 'completed',
  variants: [
    { language: 'fa', terms: ['بندر ABC-123'] },
    { language: 'zh-Hant', terms: ['港口 ABC-123'] },
  ],
};

it('retains exact map origin in previews while supporting ordinary legacy previews', () => {
  const id = 'a733f985-4bb6-46e9-ae07-a6160c001327';
  const area = { geometry: { type: 'FeatureCollection', features: [] }, sha256: 'a'.repeat(64) };
  const origin = {
    view_id: id,
    revision_id: id,
    report_id: id,
    report_version_id: id,
    report_version_number: 1,
    content_sha256: 'b'.repeat(64),
    evidence_sha256: 'c'.repeat(64),
    area,
  };
  expect(previewSchema.parse({ ...frozenPlan, area, map_origin: origin }).map_origin).toEqual(
    origin,
  );
  expect(previewSchema.parse(frozenPlan).map_origin).toBeNull();
  expect(
    previewSchema.safeParse({ ...frozenPlan, map_origin: { ...origin, revision_id: 'bad' } })
      .success,
  ).toBe(false);
});

it('preserves and renders the frozen plan independently of collection attempt outcomes', () => {
  const receipt = researchReceiptSchema.parse({ ...researchReceipt, plan: frozenPlan });
  render(<SavedCollectionPlan plan={receipt.plan!} />);
  expect(screen.getByText('بندر')).toBeVisible();
  expect(screen.getByText(/Operator-supplied language terms/)).toBeVisible();
  expect(screen.getByText(/8 requests, 20 seconds, 50 items/)).toBeVisible();
  expect(
    screen.queryByRole('region', { name: 'Automatic query translation' }),
  ).not.toBeInTheDocument();
});

it('displays the recorded translation phrases and model without claiming verified meaning', () => {
  const plan = planSchema.parse({
    ...frozenPlan,
    translation,
    tasks: [
      {
        ...frozenPlan.tasks[0],
        provenance: 'machine_translated_variant',
        query_language: 'zh-Hant',
      },
    ],
  });
  render(<SavedCollectionPlan plan={plan} />);
  const section = within(screen.getByRole('region', { name: 'Automatic query translation' }));
  expect(
    section.getByText(/Completed: generated phrases passed syntax and identifier checks only/),
  ).toBeVisible();
  expect(
    section.getByText(/Translation meaning has not been independently verified/),
  ).toBeVisible();
  expect(section.getByText('Port ABC-123')).toBeVisible();
  expect(section.getByText('بندر ABC-123')).toHaveAttribute('dir', 'auto');
  expect(section.getByText('港口 ABC-123')).toBeVisible();
  expect(section.getByText('configured-model')).toBeVisible();
  expect(section.getByText('query-translation-v1')).toBeVisible();
  expect(screen.getByText('Query language: zh-Hant')).toBeVisible();
  expect(screen.getByText(/Machine-translated search terms, meaning unverified/)).toBeVisible();
});

it.each([
  ['failed', 'Failed: no valid translation result was available; original terms were retained.'],
  [
    'unavailable',
    'Unavailable: no translation model was configured, so no translation call was made.',
  ],
])('shows the recorded %s status without suggesting completed translation', (status, message) => {
  const plan = planSchema.parse({
    ...frozenPlan,
    translation: {
      ...translation,
      status,
      variants: [],
      model: status === 'unavailable' ? '' : 'configured-model',
    },
  });
  render(<SavedCollectionPlan plan={plan} />);
  expect(screen.getByText(message)).toBeVisible();
  expect(screen.getByText('No translated phrases recorded.')).toBeVisible();
  expect(screen.queryByText(/Completed:/)).not.toBeInTheDocument();
  expect(screen.getByText('Port ABC-123')).toBeVisible();
});

it('rejects unrecognised translation status instead of rendering an invented success', () => {
  expect(
    planSchema.safeParse({ ...frozenPlan, translation: { ...translation, status: 'verified' } })
      .success,
  ).toBe(false);
});

it('retains the frozen area and distinguishes source spatial capability from ordinary support', () => {
  const area = {
    geometry: {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [0, 0],
                [1, 0],
                [1, 1],
                [0, 1],
                [0, 0],
              ],
            ],
          },
        },
      ],
    },
    sha256: 'a'.repeat(64),
  };
  const plan = planSchema.parse({
    ...frozenPlan,
    area,
    tasks: [
      {
        ...frozenPlan.tasks[0],
        supported: false,
        spatial_supported: false,
        spatial_scope: 'Country selection does not establish polygon coverage.',
      },
      {
        ...frozenPlan.tasks[0],
        source_id: 'spatial',
        spatial_supported: true,
        spatial_scope: 'Native bounding-box catalogue query.',
      },
    ],
  });
  expect(plan.area).toEqual(area);
  render(<SavedCollectionPlan plan={plan} />);
  expect(screen.getByText(/Area query unsupported: Country selection/)).toBeVisible();
  expect(screen.getByText(/Area query supported: Native bounding-box/)).toBeVisible();
  const legacy = planSchema.parse(frozenPlan);
  expect(legacy.area).toBeNull();
  expect(legacy.tasks[0]?.spatial_supported).toBe(false);
  expect(
    planSchema.safeParse({ ...frozenPlan, area: { ...area, sha256: 'invalid' } }).success,
  ).toBe(false);
});
