import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { RfStudyComparison } from './RfStudyComparison';
import { createRfDraft } from '@/lib/map/rfDraft';
import { snapshotRfStudy, type RfStudySnapshot } from '@/lib/map/rfStudy';
import { RF_ANTENNA_DEFAULTS } from '@/lib/map/rfAntenna';
const baseline = () =>
  snapshotRfStudy(
    { ...createRfDraft(), propagation: 'free-space' },
    [0, 0],
    [0.1, 0],
    { origin: 'Hill', receiver: 'Valley' },
    null,
  );
it.each([5, -5])('compares matching model margins with a signed change of %i dB', (difference) => {
  const saved = baseline();
  const current = structuredClone(saved);
  current.result!.marginDb = saved.result!.marginDb! + difference;
  const clear = vi.fn();
  render(
    <RfStudyComparison
      baseline={saved}
      draft={current.draft}
      current={() => current}
      onClear={clear}
    />,
  );
  expect(screen.getByText(/Current planning margin/)).toHaveTextContent(
    `${difference > 0 ? '+' : ''}${difference.toFixed(1)} dB against baseline`,
  );
  expect(screen.getByText('Changed inputs: None.')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Clear baseline' }));
  expect(clear).toHaveBeenCalledOnce();
});
it('shows meaningful site, model, engineering and radio changes independently of the frozen baseline', () => {
  const saved = baseline();
  const current = structuredClone(saved);
  current.origin = [1, 1];
  current.draft = {
    ...current.draft,
    values: { ...current.draft.values, frequencyMHz: '500' },
    environment: { ...current.draft.environment!, radiusKm: '10' },
    engineering: { reserveDb: '20', obstacleHeightM: '5', earthFactor: '1.1' },
    antenna: RF_ANTENNA_DEFAULTS,
    propagation: 'terrain',
    study: 'area',
    automaticHfMode: 'hf-skywave',
    radiusMode: 'manual',
  };
  saved.terrainEvidence = {
    zoom: 10,
    resolutionM: 150,
    samples: [
      [0, 0, 0],
      [0.05, 0, 5],
      [0.1, 0, 0],
    ],
    profiles: [{ bearingDegrees: 90, indices: [0, 1, 2], distancesM: [0, 5000, 10000] }],
  };
  render(
    <RfStudyComparison
      baseline={saved}
      draft={current.draft}
      current={() => current}
      onClear={vi.fn()}
    />,
  );
  for (const text of [
    'Frequency (MHz)',
    'Site coordinates',
    'Environment',
    'Planning assumptions',
    'Antenna pattern',
    'Propagation model',
    'Study type',
    'Automatic HF scenario',
    'Radius mode',
  ])
    expect(screen.getByText(/Changed inputs:/)).toHaveTextContent(text);
  expect(screen.getByText(/Baseline includes 3 terrain samples/)).toBeVisible();
  expect(saved.origin).toEqual([0, 0]);
});
it.each([
  'missing-baseline',
  'missing-current',
  'missing-margin',
  'different-model',
  'invalid-draft',
] as const)('does not invent a comparable margin for %s', (reason) => {
  const saved = baseline();
  const candidate = structuredClone(saved);
  if (reason === 'missing-baseline') saved.result = null;
  if (reason === 'missing-current') candidate.result = null;
  if (reason === 'missing-margin') candidate.result!.marginDb = null;
  if (reason === 'different-model') candidate.result!.kind = 'hf-skywave';
  const current = (): RfStudySnapshot => {
    if (reason === 'invalid-draft') throw new Error('Incomplete frequency');
    return candidate;
  };
  render(
    <RfStudyComparison
      baseline={saved}
      draft={candidate.draft}
      current={current}
      onClear={vi.fn()}
    />,
  );
  expect(screen.getByText(/Run a matching model/)).toBeVisible();
  expect(screen.queryByText(/Current planning margin/)).not.toBeInTheDocument();
  if (reason === 'missing-baseline')
    expect(screen.getByText(/Frozen result: No analysis saved/)).toBeVisible();
});
