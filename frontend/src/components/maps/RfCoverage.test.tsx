import { useState } from 'react';
import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { RfCalculatorPanel } from './RfCalculatorPanel';
import { useRfAnalysis } from './useRfAnalysis';
import { fetchTerrainElevations } from '@/lib/api/terrain';
import { createRfDraft } from '@/lib/map/rfDraft';
import type { RfDraft } from '@/lib/map/rfDraft';
import { DEFAULT_RF_INPUTS } from '@/lib/map/rfPlanning';
import { plainUser } from '@/test/fixtures';
import { useAuthStore } from '@/stores/auth';

vi.mock('@/lib/api/terrain', () => ({ fetchTerrainElevations: vi.fn() }));
beforeEach(() => {
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  vi.mocked(fetchTerrainElevations).mockImplementation((positions) =>
    Promise.resolve({
      elevations_m: positions.map(() => 0),
      zoom: 10,
      resolution_m: 100,
      provider: 'Mapzen Terrain Tiles',
      attribution: 'Fixture',
      attribution_url: 'https://example.com/',
      limitations: 'Fixture',
    }),
  );
});

it('requires a receiver for an explicit link and allows a 360 degree study without deleting a site', () => {
  const onPick = vi.fn();
  render(<RfCalculatorPanel origin={[0, 51]} onPick={onPick} />);
  fireEvent.click(screen.getByRole('button', { name: 'Transmitter → receiver' }));
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeDisabled();
  expect(screen.getByText(/Place a receiver to analyse/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: '360° area' }));
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeEnabled();
  const bubble = screen.getByRole('checkbox', { name: /coverage bubble/ });
  expect(bubble).not.toBeChecked();
  fireEvent.click(bubble);
  expect(bubble).toBeChecked();
  fireEvent.click(screen.getByRole('button', { name: 'Add receiver' }));
  expect(onPick).toHaveBeenLastCalledWith('receiver');
  expect(screen.getByRole('button', { name: 'Transmitter → receiver' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  expect(fetchTerrainElevations).not.toHaveBeenCalled();
});

it('treats bubble shading as display-only and excludes the saved receiver from a free-space area', () => {
  const changeAnalysis = vi.fn(),
    changeOverlay = vi.fn(),
    changeBubble = vi.fn();
  function Panel() {
    const [draft, setDraft] = useState<RfDraft>({ ...createRfDraft(), propagation: 'free-space' });
    return (
      <RfCalculatorPanel
        draft={draft}
        onDraftChange={setDraft}
        origin={[0, 51]}
        receiver={[1, 51]}
        onAnalysisChange={changeAnalysis}
        onOverlayChange={changeOverlay}
        onCoverageBubbleChange={changeBubble}
      />
    );
  }
  render(<Panel />);
  fireEvent.click(screen.getByRole('button', { name: '360° area' }));
  expect(screen.getByText(/saved receiver is excluded/)).toBeVisible();
  changeAnalysis.mockClear();
  changeOverlay.mockClear();
  fireEvent.click(screen.getByRole('checkbox', { name: /coverage bubble/ }));
  expect(changeBubble).toHaveBeenCalledWith(true);
  expect(changeAnalysis).not.toHaveBeenCalled();
  expect(changeOverlay).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Show estimate on map' }));
  expect(changeOverlay).toHaveBeenLastCalledWith(expect.objectContaining({ receiver: null }));
  fireEvent.click(screen.getByRole('button', { name: 'Transmitter → receiver' }));
  fireEvent.click(screen.getByRole('button', { name: 'Show estimate on map' }));
  expect(changeOverlay).toHaveBeenLastCalledWith(expect.objectContaining({ receiver: [1, 51] }));
  expect(fetchTerrainElevations).not.toHaveBeenCalled();
});

it('uses the bounded radial plan for an area even with a saved receiver and restores the link plan', async () => {
  const onChange = vi.fn();
  const { result, rerender } = renderHook(
    ({ draft }: { draft: RfDraft }) =>
      useRfAnalysis(DEFAULT_RF_INPUTS, draft, [0, 51], [0.01, 51], onChange),
    {
      initialProps: { draft: { ...createRfDraft(), study: 'area' } },
    },
  );
  expect(fetchTerrainElevations).not.toHaveBeenCalled();
  await act(() => result.current.analyse());
  expect(onChange).toHaveBeenLastCalledWith(
    expect.objectContaining({ plan: expect.objectContaining({ kind: 'radial', receiver: null }) }),
  );
  expect(vi.mocked(fetchTerrainElevations).mock.calls[0]?.[0]).toHaveLength(409);
  rerender({ draft: { ...createRfDraft(), study: 'link' } });
  await act(() => result.current.analyse());
  expect(onChange).toHaveBeenLastCalledWith(
    expect.objectContaining({
      plan: expect.objectContaining({ kind: 'path', receiver: [0.01, 51] }),
    }),
  );
  expect(vi.mocked(fetchTerrainElevations).mock.calls[1]?.[0]).toHaveLength(9);
});

it('does not silently substitute a radial study for a requested link without a receiver', async () => {
  const changed = vi.fn();
  const { result } = renderHook(() =>
    useRfAnalysis(DEFAULT_RF_INPUTS, { ...createRfDraft(), study: 'link' }, [0, 51], null, changed),
  );
  await act(() => result.current.analyse());
  expect(result.current.error).toMatch(/Place a receiver/);
  expect(fetchTerrainElevations).not.toHaveBeenCalled();
});
