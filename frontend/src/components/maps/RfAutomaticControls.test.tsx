import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { RfCalculatorPanel } from './RfCalculatorPanel';
import { createRfDraft } from '@/lib/map/rfDraft';
import { rfEnvironmentValid } from './RfModelControls';

it('chooses the radio model from frequency while keeping watts first and assumptions optional', () => {
  render(<RfCalculatorPanel origin={[0, 51]} />);
  expect(screen.getAllByRole('spinbutton')[0]).toHaveAccessibleName('Transmit power (watts)');
  expect(screen.getByText(/Automatic model · Terrain-aware/)).toBeVisible();
  expect(
    screen.getByRole('checkbox', { name: 'Choose analysis area automatically' }),
  ).toBeChecked();
  expect(screen.queryByLabelText('Area to analyse (km from transmitter)')).not.toBeInTheDocument();
  expect(
    screen.getByText('Advanced model & radio settings').closest('details'),
  ).not.toHaveAttribute('open');
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '7' } });
  expect(screen.getByText(/Automatic model · HF groundwave/)).toBeVisible();
  expect(screen.getByText(/Checks the groundwave model out to 200 km/)).toBeVisible();
  expect(screen.getByRole('button', { name: 'Analyse HF groundwave' })).toBeEnabled();
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '150' } });
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeEnabled();
});

it('makes the area an optional manual distance and restores automatic validation after an incomplete edit', () => {
  render(<RfCalculatorPanel origin={[0, 51]} />);
  const automatic = screen.getByRole('checkbox', { name: 'Choose analysis area automatically' });
  fireEvent.click(automatic);
  const radius = screen.getByLabelText('Area to analyse (km from transmitter)');
  fireEvent.change(radius, { target: { value: '' } });
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeDisabled();
  fireEvent.click(automatic);
  expect(screen.queryByLabelText('Area to analyse (km from transmitter)')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeEnabled();
  fireEvent.click(automatic);
  expect(screen.getByLabelText('Area to analyse (km from transmitter)')).toHaveValue(null);
  fireEvent.change(screen.getByLabelText('Area to analyse (km from transmitter)'), {
    target: { value: '12' },
  });
  expect(screen.getByRole('button', { name: 'Analyse terrain' })).toBeEnabled();
});

it.each(['terrain', 'hf-groundwave'] as const)(
  'hides and ignores the unused manual area in a %s receiver link',
  (mode) => {
    const draft = createRfDraft();
    draft.propagation = mode;
    draft.study = 'link';
    draft.radiusMode = 'manual';
    draft.environment!.radiusKm = '';
    if (mode === 'hf-groundwave') draft.values.frequencyMHz = '7';
    render(<RfCalculatorPanel draft={draft} origin={[0, 51]} receiver={[0.02, 51]} />);
    expect(
      screen.queryByLabelText('Area to analyse (km from transmitter)'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('checkbox', { name: 'Choose analysis area automatically' }),
    ).not.toBeInTheDocument();
    expect(rfEnvironmentValid(draft, true)).toBe(true);
    expect(rfEnvironmentValid(draft, false)).toBe(false);
    expect(
      screen.getByRole('button', {
        name: mode === 'terrain' ? 'Analyse terrain' : 'Analyse HF groundwave',
      }),
    ).toBeEnabled();
  },
);

it('preserves an explicitly chosen model until the operator restores automatic selection', () => {
  render(<RfCalculatorPanel origin={[0, 51]} />);
  fireEvent.click(screen.getByText('Advanced model & radio settings'));
  fireEvent.change(screen.getByLabelText('Propagation model'), { target: { value: 'free-space' } });
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '7' } });
  expect(screen.getByText(/Manual model · Free-space reference/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('Propagation model'), { target: { value: 'automatic' } });
  expect(screen.getByText(/Automatic model · HF groundwave/)).toBeVisible();
});

it('lets a groundwave area exclude a saved receiver and restores that site for a receiver link', () => {
  render(<RfCalculatorPanel origin={[0, 51]} receiver={[0.02, 51]} />);
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '7' } });
  expect(screen.getByRole('button', { name: 'Transmitter → receiver' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  expect(
    screen.queryByRole('checkbox', { name: 'Choose analysis area automatically' }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '360° area' }));
  expect(screen.getByText(/saved receiver is excluded/)).toBeVisible();
  expect(
    screen.getByRole('checkbox', { name: 'Choose analysis area automatically' }),
  ).toBeVisible();
  expect(screen.queryByRole('checkbox', { name: /coverage bubble/ })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Analyse HF groundwave' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Transmitter → receiver' }));
  expect(screen.queryByText(/saved receiver is excluded/)).not.toBeInTheDocument();
  expect(
    screen.queryByRole('checkbox', { name: 'Choose analysis area automatically' }),
  ).not.toBeInTheDocument();
});

it('preserves an automatic NVIS scenario when frequency is edited without retaining the equipment claim', () => {
  render(<RfCalculatorPanel origin={[0, 51]} />);
  fireEvent.change(screen.getByLabelText('Radio preset'), {
    target: { value: 'bowman-prc325-nvis' },
  });
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '8' } });
  expect(screen.getByLabelText('Radio preset')).toHaveValue('custom');
  expect(screen.getByLabelText('Propagation model')).toHaveValue('automatic');
  expect(screen.getByText(/Automatic model · HF skywave/)).toBeVisible();
  expect(screen.getByLabelText('Transmit power (watts)')).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '150' } });
  expect(screen.getByText(/Automatic model · Terrain-aware/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('Frequency (MHz)'), { target: { value: '8' } });
  expect(screen.getByText(/Automatic model · HF skywave/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('Radio preset'), { target: { value: 'hf-portable' } });
  expect(screen.getByText(/Automatic model · HF groundwave/)).toBeVisible();
});
