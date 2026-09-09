import { render, screen, fireEvent } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { RfCalculatorPanel } from './RfCalculatorPanel';

it('uses a supplied measurement explicitly and hides results for incomplete inputs', () => {
  render(<RfCalculatorPanel measuredDistanceKm={20} />);
  fireEvent.click(screen.getByRole('button', { name: /Use measured path/ }));
  expect(screen.getByLabelText('Path length (km)')).toHaveValue(20);
  expect(screen.getByText(/Beyond the model horizon/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '' } });
  expect(screen.getByRole('alert')).toHaveTextContent('Frequency');
  expect(screen.queryByText(/Estimated receive level/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '2400' } });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
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
