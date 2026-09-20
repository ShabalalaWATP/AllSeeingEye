import { useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { RfDraft } from '@/lib/map/rfDraft';
import { createRfDraft } from '@/lib/map/rfDraft';
import { RfCalculatorPanel as Calculator } from './RfCalculatorPanel';
import type { RfCalculatorPanelProps } from './RfCalculatorPanel';
function RfCalculatorPanel(props: RfCalculatorPanelProps) {
  const [draft, setDraft] = useState<RfDraft>(() => ({
    ...createRfDraft(),
    propagation: 'free-space' as const,
  }));
  return <Calculator {...props} draft={draft} onDraftChange={setDraft} />;
}

it('uses a supplied measurement explicitly and hides results for incomplete inputs', () => {
  render(<RfCalculatorPanel measuredDistanceKm={20} />);
  fireEvent.click(screen.getByRole('button', { name: /Use measured path/ }));
  expect(screen.getByLabelText('Path length (km)')).toHaveValue(20);
  expect(screen.getByRole('region', { name: 'Result explained' })).toBeVisible();
  expect(screen.getByText(/Beyond the model horizon/)).not.toBeVisible();
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '' } });
  expect(screen.getByRole('alert')).toHaveTextContent('Frequency');
  expect(screen.queryByText(/Estimated receive level/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '2400' } });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  fireEvent.click(screen.getByText('Engineering details'));
  expect(screen.getByText(/Estimated receive level/)).toBeVisible();
});

it('applies a radio preset and invalidates an old map estimate when inputs change', () => {
  const onOverlayChange = vi.fn();
  render(<RfCalculatorPanel origin={[0, 51]} onOverlayChange={onOverlayChange} overlayVisible />);
  fireEvent.change(screen.getByRole('combobox', { name: 'Radio preset' }), {
    target: { value: 'marine' },
  });
  expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(156);
  expect(screen.getByLabelText('Transmit power (dBm)')).toHaveValue(44);
  expect(onOverlayChange).toHaveBeenLastCalledWith(null);
  fireEvent.click(screen.getByRole('button', { name: 'Update map estimate' }));
  expect(onOverlayChange).toHaveBeenLastCalledWith(
    expect.objectContaining({ origin: [0, 51], receiver: null, radiusKm: expect.any(Number) }),
  );
  fireEvent.change(screen.getByLabelText('Transmit height above ground (m)'), {
    target: { value: '20' },
  });
  expect(screen.getByRole('combobox', { name: 'Radio preset' })).toHaveValue('custom');
  expect(onOverlayChange).toHaveBeenLastCalledWith(null);
  fireEvent.click(screen.getByRole('button', { name: 'Clear map estimate' }));
  expect(onOverlayChange).toHaveBeenLastCalledWith(null);
});

it('requires a transmitter and supports map placement and cancellation', () => {
  const onPick = vi.fn();
  const onOverlayChange = vi.fn();
  const { rerender } = render(
    <RfCalculatorPanel onPick={onPick} onOverlayChange={onOverlayChange} />,
  );
  expect(screen.getByRole('button', { name: 'Show estimate on map' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Place transmitter' }));
  expect(onPick).toHaveBeenLastCalledWith('origin');
  rerender(
    <RfCalculatorPanel onPick={onPick} onOverlayChange={onOverlayChange} picking="origin" />,
  );
  expect(screen.getByRole('status')).toHaveTextContent('Click the map');
  fireEvent.click(screen.getByRole('button', { name: 'Place transmitter' }));
  expect(onPick).toHaveBeenLastCalledWith(null);
  fireEvent.click(screen.getByRole('button', { name: 'Add receiver' }));
  expect(onPick).toHaveBeenLastCalledWith('receiver');
});

it('uses the geodesic transmitter-to-receiver distance and prevents zero-radius output', () => {
  const onOverlayChange = vi.fn();
  render(
    <RfCalculatorPanel origin={[0, 51]} receiver={[0.1, 51]} onOverlayChange={onOverlayChange} />,
  );
  const distance = screen.getByLabelText('Path length (km)');
  expect(distance).toHaveAttribute('readonly');
  expect(Number((distance as HTMLInputElement).value)).toBeCloseTo(7.02, 1);
  fireEvent.click(screen.getByRole('button', { name: 'Show estimate on map' }));
  expect(onOverlayChange).toHaveBeenLastCalledWith(
    expect.objectContaining({ receiver: [0.1, 51] }),
  );
  fireEvent.change(screen.getByLabelText('Transmit height above ground (m)'), {
    target: { value: '0' },
  });
  fireEvent.change(screen.getByLabelText('Receive height above ground (m)'), {
    target: { value: '0' },
  });
  expect(screen.getByRole('button', { name: 'Show estimate on map' })).toBeDisabled();
  expect(screen.getByRole('status')).toHaveTextContent('below 1 metre');
});

it('chooses terrain automatically, keeps watts first and requires explicit valid analysis', () => {
  const change = vi.fn();
  render(<Calculator origin={[0, 51]} onAnalysisChange={change} />);
  expect(screen.getByRole('combobox', { name: 'Propagation model' })).toHaveValue('automatic');
  expect(screen.getByText(/Automatic model · Terrain-aware/)).toBeVisible();
  expect(screen.queryByText(/Estimated receive level/)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeEnabled();
  const watts = screen.getByRole('spinbutton', { name: 'Transmit power (watts)' });
  expect(watts).toBeVisible();
  expect(watts.closest('details')).toBeNull();
  expect(screen.getAllByRole('spinbutton')[0]).toBe(watts);
  fireEvent.change(screen.getByLabelText('Transmit power (watts)'), { target: { value: '20' } });
  expect(screen.getByLabelText('Transmit power (dBm)')).toHaveValue(30 + 10 * Math.log10(20));
  expect(change).toHaveBeenLastCalledWith(null);
  fireEvent.change(screen.getByLabelText('Transmit power (watts)'), { target: { value: '' } });
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeDisabled();
});
it('preserves custom model environment when changing a radio preset and honours its HF suggestion', () => {
  function Panel() {
    const [draft, setDraft] = useState<RfDraft>(() => ({
      ...createRfDraft(),
      environment: { ...createRfDraft().environment!, conductivitySm: '0.02' },
    }));
    return <Calculator draft={draft} onDraftChange={setDraft} />;
  }
  render(<Panel />);
  fireEvent.change(screen.getByRole('combobox', { name: 'Radio preset' }), {
    target: { value: 'hf-portable' },
  });
  expect(screen.getByRole('combobox', { name: 'Propagation model' })).toHaveValue('automatic');
  expect(screen.getByText(/Automatic model · HF groundwave/)).toBeVisible();
  expect(screen.getByLabelText('Ground conductivity (S/m)')).toHaveValue(0.02);
  expect(screen.getByLabelText('Transmit power (watts)')).toHaveValue(20);
});

it('does not apply a receive budget or unused radio-field validation to skywave', () => {
  const draft = createRfDraft();
  draft.propagation = 'hf-skywave';
  draft.values.frequencyMHz = '7';
  draft.values.transmitDbm = '';
  draft.values.distanceKm = '';
  render(<Calculator draft={draft} origin={[0, 51]} />);
  expect(screen.getByRole('button', { name: 'Calculate skywave scenario' })).toBeEnabled();
  expect(screen.getByLabelText('Transmit power (watts)')).toBeDisabled();
  expect(screen.getByText(/Power is not used by the skywave geometry scenario/)).toBeVisible();
  expect(screen.queryByLabelText('Path length (km)')).not.toBeInTheDocument();
  expect(screen.queryByText(/Estimated receive level/)).not.toBeInTheDocument();
});

it.each(['terrain', 'hf-groundwave'] as const)(
  'ignores an unused blank path length for %s',
  (propagation) => {
    const draft = createRfDraft();
    draft.propagation = propagation;
    draft.values.distanceKm = '';
    if (propagation === 'hf-groundwave') draft.values.frequencyMHz = '7';
    render(<Calculator draft={draft} origin={[0, 51]} />);
    expect(screen.queryByLabelText('Path length (km)')).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: propagation === 'terrain' ? 'Analyse terrain' : 'Analyse HF groundwave',
      }),
    ).toBeEnabled();
  },
);
it('moves HF to terrain for VHF presets, preserves an explicit free-space choice and applies NVIS angles', () => {
  render(<Calculator />);
  const choose = (id: string) =>
    fireEvent.change(screen.getByRole('combobox', { name: 'Radio preset' }), {
      target: { value: id },
    });
  choose('hf-nvis');
  expect(screen.getByLabelText('Minimum launch elevation (degrees)')).toHaveValue(60);
  expect(screen.getByLabelText('Maximum launch elevation (degrees)')).toHaveValue(90);
  choose('marine');
  expect(screen.getByLabelText('Propagation model')).toHaveValue('automatic');
  expect(screen.getByText(/Automatic model · Terrain-aware/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('Propagation model'), { target: { value: 'free-space' } });
  choose('hf-portable');
  expect(screen.getByLabelText('Propagation model')).toHaveValue('free-space');
  choose('custom');
  expect(screen.getByLabelText('Propagation model')).toHaveValue('free-space');
});
