import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { CoordinateWorkbench } from './CoordinateWorkbench';

const clipboardDescriptor = Object.getOwnPropertyDescriptor(navigator, 'clipboard');
afterEach(() => {
  if (clipboardDescriptor) Object.defineProperty(navigator, 'clipboard', clipboardDescriptor);
  else Reflect.deleteProperty(navigator, 'clipboard');
});

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

it('converts valid southern UTM input and copies the displayed latitude/longitude', async () => {
  const write = vi.fn(() => Promise.resolve());
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: write },
  });
  const navigate = vi.fn();
  render(<CoordinateWorkbench onNavigate={navigate} />);
  fireEvent.change(screen.getByLabelText('Input format'), { target: { value: 'utm' } });
  fireEvent.change(screen.getByLabelText('UTM zone'), { target: { value: '56' } });
  fireEvent.change(screen.getByLabelText('Hemisphere'), { target: { value: 'S' } });
  fireEvent.change(screen.getByLabelText('Easting (m)'), { target: { value: '333568.94' } });
  fireEvent.change(screen.getByLabelText('Northing (m)'), { target: { value: '6247473.34' } });
  fireEvent.click(screen.getByRole('button', { name: 'Convert coordinates' }));
  fireEvent.click(screen.getByRole('button', { name: 'Go to location' }));
  const point = navigate.mock.calls[0]?.[0] as [number, number];
  expect(point[0]).toBeCloseTo(151.2, 4);
  expect(point[1]).toBeCloseTo(-33.9, 4);
  fireEvent.click(screen.getByRole('button', { name: 'Copy coordinates' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Coordinates copied');
  expect(write).toHaveBeenCalledWith(`${point[1].toFixed(6)}, ${point[0].toFixed(6)}`);
});

it('keeps polar coordinates usable when UTM is unavailable and reports clipboard denial', async () => {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: vi.fn(() => Promise.reject(new Error('Denied'))) },
  });
  render(<CoordinateWorkbench onNavigate={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Latitude'), { target: { value: '85' } });
  fireEvent.change(screen.getByLabelText('Longitude'), { target: { value: '20' } });
  fireEvent.click(screen.getByRole('button', { name: 'Convert coordinates' }));
  expect(screen.getByText(/UTM is unavailable outside/)).toBeVisible();
  expect(screen.getByRole('button', { name: 'Go to location' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Copy coordinates' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Copy is unavailable');
});
