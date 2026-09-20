import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { RfCalculatorPanel } from './RfCalculatorPanel';
import { fetchTerrainElevations } from '@/lib/api/terrain';
import { plainUser } from '@/test/fixtures';
import { useAuthStore } from '@/stores/auth';
import { createRfDraft } from '@/lib/map/rfDraft';

vi.mock('@/lib/api/terrain', () => ({ fetchTerrainElevations: vi.fn() }));
const fixture = (
  positions: readonly unknown[],
): Awaited<ReturnType<typeof fetchTerrainElevations>> => ({
  elevations_m: positions.map(() => 0),
  zoom: 10,
  resolution_m: 100,
  provider: 'Mapzen Terrain Tiles',
  attribution: 'Fixture',
  attribution_url: 'https://example.com/',
  limitations: 'Fixture',
});
beforeEach(() => {
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  vi.mocked(fetchTerrainElevations).mockImplementation((positions) =>
    Promise.resolve(fixture(positions)),
  );
});

it('starts with an editable configuration and opens results only after explicit completion', async () => {
  let resolve: ((value: Awaited<ReturnType<typeof fetchTerrainElevations>>) => void) | undefined;
  vi.mocked(fetchTerrainElevations).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  render(<RfCalculatorPanel origin={[0, 51]} receiver={[0.01, 51]} />);
  expect(screen.getByRole('tab', { name: /Configure/ })).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('tab', { name: /Results/ })).toBeDisabled();
  expect(fetchTerrainElevations).not.toHaveBeenCalled();
  const analyse = screen.getByRole('button', { name: 'Analyse terrain' });
  analyse.focus();
  fireEvent.click(analyse);
  expect(screen.getByRole('button', { name: 'Analysing...' })).toBeDisabled();
  expect(screen.getByRole('tab', { name: /Results/ })).toBeDisabled();
  await act(async () => {
    resolve?.(fixture(vi.mocked(fetchTerrainElevations).mock.calls[0]![0]));
    await Promise.resolve();
  });
  expect(screen.getByRole('tab', { name: /Results/ })).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('tab', { name: /Results/ })).toHaveFocus();
  expect(screen.getByLabelText('Terrain radio analysis')).toBeVisible();
  expect(screen.queryByLabelText('Frequency (MHz)')).not.toBeInTheDocument();
  const edit = screen.getByRole('button', { name: 'Edit study' });
  edit.focus();
  fireEvent.click(edit);
  expect(screen.getByRole('tab', { name: /Configure/ })).toHaveFocus();
  expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(900);
  expect(screen.getByRole('tab', { name: /Results/ })).toBeEnabled();
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '950' } });
  expect(screen.getByRole('tab', { name: /Results/ })).toBeDisabled();
  expect(fetchTerrainElevations).toHaveBeenCalledTimes(1);
});

it('supports keyboard tab navigation, retains analysis while reviewing settings and clears explicitly', async () => {
  render(<RfCalculatorPanel origin={[0, 51]} receiver={[0.01, 51]} />);
  const configure = screen.getByRole('tab', { name: /Configure/ });
  fireEvent.keyDown(configure, { key: 'ArrowRight' });
  expect(configure).toHaveFocus();
  expect(configure).toHaveAttribute('aria-selected', 'true');
  fireEvent.keyDown(configure, { key: 'Escape' });
  fireEvent.click(screen.getByRole('button', { name: 'Analyse terrain' }));
  await screen.findByLabelText('Terrain radio analysis');
  const results = screen.getByRole('tab', { name: /Results/ });
  fireEvent.keyDown(results, { key: 'Home' });
  expect(configure).toHaveFocus();
  expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(900);
  fireEvent.keyDown(configure, { key: 'End' });
  expect(results).toHaveFocus();
  fireEvent.keyDown(results, { key: 'ArrowLeft' });
  expect(configure).toHaveFocus();
  fireEvent.keyDown(configure, { key: 'ArrowRight' });
  expect(results).toHaveFocus();
  const clear = screen.getByRole('button', { name: 'Clear analysis' });
  clear.focus();
  fireEvent.click(clear);
  expect(configure).toHaveFocus();
  expect(results).toBeDisabled();
  expect(configure).toHaveAttribute('aria-selected', 'true');
  expect(screen.queryByLabelText('Terrain radio analysis')).not.toBeInTheDocument();
});

it('keeps failed analysis on Configure so the operator can correct and retry', async () => {
  vi.mocked(fetchTerrainElevations).mockRejectedValue(new Error('Unavailable'));
  render(<RfCalculatorPanel origin={[0, 51]} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyse terrain' }));
  expect(await screen.findByRole('alert')).toBeVisible();
  expect(screen.getByRole('tab', { name: /Results/ })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeEnabled();
});

it('leaves focus on the map when analysis completes after the operator moves outside the panel', async () => {
  let resolve: ((value: Awaited<ReturnType<typeof fetchTerrainElevations>>) => void) | undefined;
  vi.mocked(fetchTerrainElevations).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  render(
    <>
      <button type="button">Map control</button>
      <RfCalculatorPanel origin={[0, 51]} receiver={[0.01, 51]} />
    </>,
  );
  const analyse = screen.getByRole('button', { name: 'Analyse terrain' });
  analyse.focus();
  fireEvent.click(analyse);
  const map = screen.getByRole('button', { name: 'Map control' });
  map.focus();
  await act(async () => {
    resolve?.(fixture(vi.mocked(fetchTerrainElevations).mock.calls[0]![0]));
    await Promise.resolve();
  });
  expect(screen.getByRole('tab', { name: /Results/ })).toHaveAttribute('aria-selected', 'true');
  expect(map).toHaveFocus();
});

it('exposes equipment assumptions on demand and shows the active planning reserve', () => {
  const draft = { ...createRfDraft(), propagation: 'free-space' as const };
  render(<RfCalculatorPanel draft={draft} origin={[0, 51]} onOverlayChange={vi.fn()} />);
  fireEvent.click(screen.getByText('Preset details & assumptions'));
  expect(screen.getByText(/Presets do not establish current network settings/)).toBeVisible();
  fireEvent.click(screen.getByText('Engineering details'));
  expect(screen.getByText(/10 dB planning reserve applied/)).toBeVisible();
});

it('invalidates the previous result when an engineering allowance is incomplete', () => {
  render(<RfCalculatorPanel origin={[0, 51]} />);
  fireEvent.click(screen.getByText('Advanced model & radio settings'));
  fireEvent.change(screen.getByLabelText('Planning reserve (dB)'), { target: { value: '' } });
  expect(screen.getByRole('alert')).toHaveTextContent('Planning reserve');
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeDisabled();
});
