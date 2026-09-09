import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { RfCalculatorPanel } from '@/components/maps/RfCalculatorPanel';
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
});
