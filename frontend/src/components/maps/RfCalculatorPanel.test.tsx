import { render, screen, fireEvent } from '@testing-library/react';
import { expect, it } from 'vitest';
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
