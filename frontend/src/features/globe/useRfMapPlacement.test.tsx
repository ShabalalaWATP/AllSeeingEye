import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { SketchDrag } from '@/lib/map/MapEngine';
import { RfCalculatorPanel } from '@/components/maps/RfCalculatorPanel';
import { snapshotRfStudy } from '@/lib/map/rfStudy';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser } from '@/test/fixtures';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { useRfMapPlacement } from './useRfMapPlacement';

function fakeEngine() {
  const listeners = new Set<(point: { lon: number; lat: number }) => void>();
  const engine = {
    onClick: (callback: (point: { lon: number; lat: number }) => void) => {
      listeners.add(callback);
      return () => {
        listeners.delete(callback);
      };
    },
  } as GlobeEngineHandle;
  return {
    engine,
    click: (lon: number, lat: number) => listeners.forEach((callback) => callback({ lon, lat })),
  };
}

function Harness({ open, engine }: { open: boolean; engine: GlobeEngineHandle }) {
  const rf = useRfMapPlacement(engine, true);
  return (
    <>
      {open && (
        <RfCalculatorPanel
          origin={rf.origin}
          receiver={rf.receiver}
          picking={rf.picking}
          onPick={rf.setPicking}
          draft={rf.draft}
          onDraftChange={rf.setDraft}
          onClearReceiver={rf.clearReceiver}
          onOverlayChange={rf.setEstimate}
          overlayVisible={rf.estimate !== null}
        />
      )}
      <output aria-label="Map estimate radius">{rf.estimate?.radiusKm ?? 'none'}</output>
    </>
  );
}

it('keeps the selected radio preset and its map estimate when reopening the tool', () => {
  const { engine, click } = fakeEngine();
  const { rerender } = render(<Harness open engine={engine} />);
  fireEvent.change(screen.getByRole('combobox', { name: 'Propagation model' }), {
    target: { value: 'free-space' },
  });
  fireEvent.change(screen.getByRole('combobox', { name: 'Radio preset' }), {
    target: { value: 'marine' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Place transmitter' }));
  act(() => click(0, 51));
  fireEvent.click(screen.getByRole('button', { name: 'Show estimate on map' }));
  const radius = screen.getByLabelText('Map estimate radius').textContent;
  expect(Number(radius)).toBeGreaterThan(0);
  rerender(<Harness open={false} engine={engine} />);
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Map estimate radius')).toHaveTextContent(radius);
  rerender(<Harness open engine={engine} />);
  expect(screen.getByRole('combobox', { name: 'Radio preset' })).toHaveValue('marine');
  expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(156);
  fireEvent.click(screen.getByRole('button', { name: 'Update map estimate' }));
  expect(screen.getByLabelText('Map estimate radius')).toHaveTextContent(radius);
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '' } });
  expect(screen.getByLabelText('Map estimate radius')).toHaveTextContent('none');
  rerender(<Harness open={false} engine={engine} />);
  rerender(<Harness open engine={engine} />);
  expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(null);
  expect(screen.getByRole('alert')).toHaveTextContent('Frequency');
});

it.each(['access', 'account'] as const)(
  'resets the RF draft with positions and estimate after %s changes',
  (change) => {
    useAuthStore.setState({ user: plainUser, status: 'authenticated' });
    const { engine, click } = fakeEngine();
    render(<Harness open engine={engine} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Propagation model' }), {
      target: { value: 'free-space' },
    });
    fireEvent.change(screen.getByRole('combobox', { name: 'Radio preset' }), {
      target: { value: 'wifi24' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Place transmitter' }));
    act(() => click(0, 51));
    fireEvent.click(screen.getByRole('button', { name: 'Show estimate on map' }));
    act(() => {
      if (change === 'access') invalidateWorkspaceAccess();
      else useAuthStore.setState({ user: adminUser });
    });
    expect(screen.getByRole('combobox', { name: 'Radio preset' })).toHaveValue('custom');
    expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(900);
    expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeDisabled();
    expect(screen.getByLabelText('Map estimate radius')).toHaveTextContent('none');
  },
);

it('removes the receiver and obsolete link while keeping the transmitter and radio draft', () => {
  const { engine, click } = fakeEngine();
  render(<Harness open engine={engine} />);
  fireEvent.change(screen.getByRole('combobox', { name: 'Propagation model' }), {
    target: { value: 'free-space' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Place transmitter' }));
  act(() => click(0, 51));
  fireEvent.click(screen.getByRole('button', { name: 'Add receiver' }));
  act(() => click(0.1, 51));
  fireEvent.click(screen.getByRole('button', { name: 'Show estimate on map' }));
  fireEvent.click(screen.getByRole('button', { name: 'Remove receiver, keep transmitter' }));
  expect(screen.getByRole('button', { name: 'Move transmitter' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Add receiver' })).toBeVisible();
  expect(screen.getByLabelText('Path length (km)')).not.toHaveAttribute('readonly');
  expect(screen.getByLabelText('Map estimate radius')).toHaveTextContent('none');
  expect(screen.getByRole('button', { name: 'Show estimate on map' })).toBeEnabled();
  expect(screen.getByRole('button', { name: '360° area' })).toHaveAttribute('aria-pressed', 'true');
});

it('edits and swaps named sites while retaining an independent baseline until access changes', () => {
  const { engine } = fakeEngine();
  const { result } = renderHook(() => useRfMapPlacement(engine, true));
  act(() => {
    result.current.setSite('origin', [0, 51], 'Hill');
    result.current.setSite('receiver', [1, 51], 'Valley');
  });
  const saved = snapshotRfStudy(
    result.current.draft,
    result.current.origin,
    result.current.receiver,
    result.current.siteNames,
    null,
  );
  act(() => {
    result.current.setBaseline(saved);
    result.current.setProfilePoint([0.5, 51]);
    result.current.swapSites();
  });
  expect(result.current.origin).toEqual([1, 51]);
  expect(result.current.siteNames.origin).toBe('Valley');
  expect(result.current.baseline?.origin).toEqual([0, 51]);
  expect(result.current.profilePoint).toBeNull();
  act(() => result.current.restoreStudy(saved));
  expect(result.current.origin).toEqual([0, 51]);
  expect(result.current.analysis).toBeNull();
  act(() => invalidateWorkspaceAccess());
  expect(result.current.baseline).toBeNull();
  expect(result.current.siteNames).toEqual({ origin: '', receiver: '' });
});

function dragEngine() {
  const base = fakeEngine();
  const listeners = new Set<(event: SketchDrag) => void>();
  return {
    ...base,
    engine: {
      ...base.engine,
      getZoom: () => 10,
      onDrag: (handler: (event: SketchDrag) => void) => {
        listeners.add(handler);
        return () => {
          listeners.delete(handler);
        };
      },
    },
    drag: (event: SketchDrag) => listeners.forEach((handler) => handler(event)),
  };
}
it('moves only the armed site after a near-marker drag start and invalidates obsolete analysis', () => {
  const engine = dragEngine();
  const { result } = renderHook(() => useRfMapPlacement(engine.engine, true));
  act(() => {
    result.current.setSite('origin', [0, 51]);
    result.current.setSite('receiver', [1, 51]);
    result.current.setEstimate({
      origin: [0, 51],
      receiver: [1, 51],
      radiusKm: 5,
      horizonKm: 5,
      sensitivityDistanceKm: 5,
      label: 'Old reference',
    });
  });
  act(() => result.current.setDragSite('origin'));
  const event = (phase: SketchDrag['phase'], lon: number): SketchDrag => ({
    phase,
    start: { lon: 0, lat: 51 },
    current: { lon, lat: 51 },
  });
  act(() => engine.drag(event('start', 0)));
  expect(result.current.estimate).toBeNull();
  act(() => engine.drag(event('move', 0.1)));
  expect(result.current.origin).toEqual([0.1, 51]);
  expect(result.current.receiver).toEqual([1, 51]);
  act(() => engine.drag(event('end', 0.2)));
  expect(result.current.origin).toEqual([0.2, 51]);
  expect(result.current.picking).toBeNull();
  act(() => engine.click(2, 52));
  expect(result.current.origin).toEqual([0.2, 51]);
});
it('rejects distant drag starts and restores the committed site after cancel or access changes', () => {
  const engine = dragEngine();
  const { result } = renderHook(() => useRfMapPlacement(engine.engine, true));
  act(() => {
    result.current.setSite('origin', [0, 51]);
  });
  act(() => result.current.setDragSite('origin'));
  const event = (phase: SketchDrag['phase'], start = 0, current = 0.1): SketchDrag => ({
    phase,
    start: { lon: start, lat: 51 },
    current: { lon: current, lat: 51 },
  });
  act(() => {
    engine.drag(event('start', 1));
    engine.drag(event('end', 1, 2));
  });
  expect(result.current.origin).toEqual([0, 51]);
  act(() => engine.drag(event('start', 0, 0)));
  act(() => engine.drag(event('move')));
  expect(result.current.origin).toEqual([0.1, 51]);
  act(() => engine.drag(event('cancel')));
  expect(result.current.origin).toEqual([0, 51]);
  expect(result.current.picking).toBeNull();
  act(() => result.current.setDragSite('origin'));
  act(() => engine.drag(event('start', 0, 0)));
  act(() => engine.drag(event('move')));
  act(() => invalidateWorkspaceAccess());
  act(() => engine.drag(event('end')));
  expect(result.current.origin).toBeNull();
});

it('clears radio sites and saved comparison while retaining engineering configuration', () => {
  const { engine } = fakeEngine();
  const { result } = renderHook(() => useRfMapPlacement(engine, true));
  act(() => {
    result.current.setSite('origin', [0, 51], 'Private site');
    result.current.setDraft({
      ...result.current.draft,
      engineering: { reserveDb: '15', obstacleHeightM: '5', earthFactor: '1.33' },
    });
  });
  const baseline = snapshotRfStudy(
    result.current.draft,
    result.current.origin,
    null,
    result.current.siteNames,
    null,
  );
  act(() => result.current.setBaseline(baseline));
  act(() => result.current.clearSites());
  expect(result.current.origin).toBeNull();
  expect(result.current.receiver).toBeNull();
  expect(result.current.baseline).toBeNull();
  expect(result.current.siteNames.origin).toBe('');
  expect(result.current.draft.engineering?.reserveDb).toBe('15');
});
