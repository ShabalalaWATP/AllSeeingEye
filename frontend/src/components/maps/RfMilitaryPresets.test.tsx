import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { RfCalculatorPanel } from './RfCalculatorPanel';

function choose(id: string) {
  fireEvent.change(screen.getByRole('combobox', { name: 'Radio preset' }), {
    target: { value: id },
  });
}

it('groups Bowman and other military equipment and exposes the selected public specification', () => {
  render(<RfCalculatorPanel />);
  const chooser = screen.getByRole('combobox', { name: 'Radio preset' });
  expect(
    within(chooser).getByRole('group', { name: 'Bowman planning scenarios' }).children,
  ).toHaveLength(4);
  expect(
    within(chooser).getByRole('group', { name: 'Other military radios' }).children,
  ).toHaveLength(9);
  choose('prc152a-uhf');
  expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(350);
  expect(screen.getByLabelText('Transmit power (watts)')).toHaveValue(5);
  expect(screen.getByLabelText('Published radio specifications')).toHaveTextContent('762–870 MHz');
  expect(screen.getByText(/Published equipment data with editable planning inputs/)).toBeVisible();
  expect(
    screen.getByRole('link', { name: 'L3Harris AN/PRC-152A datasheet', hidden: true }),
  ).toHaveAttribute('href', expect.stringContaining('l3harris.com/'));
});

it('switches Bowman groundwave, NVIS and VHF models without running a network analysis', () => {
  const onAnalysisChange = vi.fn();
  render(<RfCalculatorPanel origin={[0, 51]} onAnalysisChange={onAnalysisChange} />);
  choose('bowman-prc325-groundwave');
  expect(screen.getByLabelText('Propagation model')).toHaveValue('hf-groundwave');
  expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(7);
  expect(screen.getByLabelText('Transmit power (watts)')).toHaveValue(20);
  expect(screen.getByLabelText('Transmit height above ground (m)')).toHaveValue(3);
  expect(screen.getByText(/Illustrative configuration/)).toBeVisible();
  expect(screen.queryByLabelText('Published radio specifications')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Analyse HF groundwave' })).toBeEnabled();
  choose('bowman-prc325-nvis');
  expect(screen.getByLabelText('Propagation model')).toHaveValue('hf-skywave');
  expect(screen.getByLabelText('Minimum launch elevation (degrees)')).toHaveValue(60);
  expect(screen.getByLabelText('Maximum launch elevation (degrees)')).toHaveValue(90);
  expect(screen.getByLabelText('Transmit power (watts)')).toBeDisabled();
  choose('bowman-vhf-vehicle');
  expect(screen.getByLabelText('Propagation model')).toHaveValue('terrain');
  expect(screen.getByLabelText('Transmit power (watts)')).toHaveValue(50);
  expect(screen.getByLabelText('Transmit height above ground (m)')).toHaveValue(3);
  expect(onAnalysisChange.mock.calls.every(([value]) => value === null)).toBe(true);
});

it('updates the link budget and clears equipment claims when the operator customises a preset', () => {
  const onOverlayChange = vi.fn();
  render(<RfCalculatorPanel origin={[0, 51]} onOverlayChange={onOverlayChange} overlayVisible />);
  fireEvent.change(screen.getByLabelText('Propagation model'), { target: { value: 'free-space' } });
  choose('sincgars-rt1702-rfpa');
  expect(screen.getByLabelText('Propagation model')).toHaveValue('free-space');
  expect(onOverlayChange).toHaveBeenLastCalledWith(null);
  fireEvent.click(screen.getByRole('button', { name: 'Update map estimate' }));
  expect(onOverlayChange).toHaveBeenLastCalledWith(
    expect.objectContaining({
      origin: [0, 51],
      radiusKm: expect.any(Number),
    }),
  );
  expect(screen.getByLabelText('Frequency (MHz)')).toHaveValue(60);
  fireEvent.change(screen.getByLabelText('Transmit power (watts)'), { target: { value: '12' } });
  expect(screen.getByLabelText('Radio preset')).toHaveValue('custom');
  expect(screen.queryByLabelText('Published radio specifications')).not.toBeInTheDocument();
  expect(onOverlayChange).toHaveBeenLastCalledWith(null);
});
