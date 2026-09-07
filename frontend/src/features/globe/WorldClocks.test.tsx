import { render, screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { WorldClocks } from './WorldClocks';

afterEach(() => vi.useRealTimers());

it.each([
  ['2026-01-15T12:00:00Z', '12:00', '17:30', '23:00'],
  ['2026-07-15T12:00:00Z', '13:00', '17:30', '22:00'],
])('uses local timezones and seasonal offsets at %s', (date, london, mumbai, canberra) => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(date));
  render(<WorldClocks />);
  const panel = screen.getByRole('region', { name: 'World clocks' });
  for (const [city, time] of [
    ['London', london],
    ['Mumbai', mumbai],
    ['Canberra', canberra],
  ]) {
    const cell = within(panel).getByText(city ?? '').parentElement?.parentElement;
    expect(cell).toHaveTextContent(time ?? '');
  }
  expect(within(panel).getByText('Tallinn')).toBeInTheDocument();
  expect(panel.querySelectorAll('time')).toHaveLength(10);
});
