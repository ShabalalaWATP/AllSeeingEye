import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { applySession } from '@/test/render';
import { previewSchema } from '@/lib/api/researchPlan';
import { ResearchPlanEditor } from './ResearchPlanEditor';
import { useResearchPlan } from './useResearchPlan';
function Harness() {
  const plan = useResearchPlan({
    question: 'What is recorded here?',
    windowHours: '24',
    languages: ['en'],
    mode: 'quick',
    focus: 'general',
    subject: '',
    country: '',
  });
  const snapshot = previewSchema.parse({
    question: 'What is recorded here?',
    since: '2026-09-01T00:00:00Z',
    until: '2026-09-02T00:00:00Z',
    languages: ['en'],
    mode: 'quick',
    focus: 'general',
    subject: null,
    country_iso: null,
    area: { geometry: { type: 'Point', coordinates: [0, 0] }, sha256: 'a'.repeat(64) },
    tasks: [
      {
        source_id: 'unavailable',
        source_name: 'Unavailable source',
        selected: true,
        supported: false,
        language: 'en',
        terms: ['Legacy task'],
        purpose: 'disambiguation',
        candidate_id: 'missing-candidate',
        provenance: 'operator_supplied_task',
        temporal_scope: 'Fixed dates',
        spatial_supported: false,
        spatial_scope: 'Geometry unsupported',
      },
    ],
    request_limit: 6,
    seconds_limit: 45,
    item_limit: 200,
    policy_version: 'legacy',
    model_calls: 0,
    translation_calls: 0,
    replans: 0,
  });
  return <ResearchPlanEditor plan={{ ...plan, snapshot, sourceIds: [] }} languages={['en']} area />;
}
it('explains unsupported legacy preview tasks and warns when area sources are all deselected', async () => {
  applySession('user');
  render(<Harness />);
  await userEvent.click(screen.getByText('Collection plan (required)'));
  expect(screen.getByText(/Select at least one supported spatial source/)).toBeVisible();
  expect(screen.getByText(/Hypothesis: missing-candidate/)).toBeVisible();
  expect(screen.getByText(/Unavailable for these preview inputs/)).toBeVisible();
  expect(screen.getByText(/Area query unsupported: Geometry unsupported/)).toBeVisible();
  expect(screen.getByRole('checkbox', { name: 'Unavailable source' })).not.toBeChecked();
});
