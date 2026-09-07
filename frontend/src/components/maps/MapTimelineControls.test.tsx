import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { savedMapFixture } from '@/test/fixtures.savedMaps';
import ReportEvidenceMap from './ReportEvidenceMap';

const scene = {
  ...report.version.evidence[0]!,
  label: 'E1',
  title: 'Catalogue scene',
  published_at: null,
  observation: {
    acquired_at: '2026-09-01T10:00:00Z',
    processed_at: null,
    collection_id: 'sentinel-2-l2a',
    item_id: 'scene',
    limitations: 'Metadata only',
    scene_cloud_cover: null,
  },
};
beforeEach(() => applySession('user'));

it('starts new area maps on acquisition dates and applies an explicit basis change', async () => {
  render(
    <ReportEvidenceMap
      reportId="r"
      version={1}
      evidence={[scene]}
      initialTimeBasis="acquisition_or_publication"
    />,
  );
  const user = userEvent.setup();
  expect(screen.getByLabelText('Timeline time basis')).toHaveValue('acquisition_or_publication');
  await user.selectOptions(
    screen.getByLabelText('Acquisition / publication timeline (UTC)'),
    '2026-09-01',
  );
  expect(
    within(screen.getByRole('list', { name: 'Map evidence' })).getByText(/Catalogue scene/),
  ).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Timeline time basis'), 'publication');
  expect(screen.queryByRole('button', { name: /E1: Catalogue scene/ })).not.toBeInTheDocument();
  await user.selectOptions(
    screen.getByLabelText('Timeline time basis'),
    'acquisition_or_publication',
  );
  expect(
    within(screen.getByRole('list', { name: 'Map evidence' })).getByText(/Catalogue scene/),
  ).toBeInTheDocument();
});

it('preserves a saved publication basis even when the report default is acquisition', () => {
  render(
    <ReportEvidenceMap
      reportId="r"
      version={1}
      evidence={[scene]}
      savedView={savedMapFixture}
      initialTimeBasis="acquisition_or_publication"
    />,
  );
  expect(screen.getByLabelText('Timeline time basis')).toHaveValue('publication');
  expect(screen.getByLabelText('Publication timeline (UTC)')).toBeInTheDocument();
});
