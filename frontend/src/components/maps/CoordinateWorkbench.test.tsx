import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { CoordinateWorkbench } from './CoordinateWorkbench';

it('converts explicitly and navigates with longitude first without network requests', () => {
  const navigate = vi.fn();
  render(<CoordinateWorkbench onNavigate={navigate} />);
  fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: '51 30 0 N' } });
  fireEvent.change(screen.getByLabelText('Longitude'), { target: { value: '0 7 12 W' } });
  fireEvent.click(screen.getByRole('button', { name: 'Convert coordinates' }));
  expect(screen.getByText('51.500000, -0.120000')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Go to location' }));
  expect(navigate).toHaveBeenCalledWith([-0.12, 51.5]);
  fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: '91' } });
  expect(screen.queryByRole('button', { name: 'Go to location' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Convert coordinates' }));
  expect(screen.getByRole('alert')).toHaveTextContent('Latitude must');
});

it('does not coerce empty UTM fields to a location', () => {
  render(<CoordinateWorkbench onNavigate={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Input format'), { target: { value: 'utm' } });
  fireEvent.click(screen.getByRole('button', { name: 'Convert coordinates' }));
  expect(screen.getByRole('alert')).toHaveTextContent('Enter the zone, easting and northing');
});
