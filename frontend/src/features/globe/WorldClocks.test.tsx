import { render, screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { WorldClocks } from './WorldClocks';

afterEach(() => vi.useRealTimers());

it.each([
  ['2026-01-15T12:00:00Z', '12:00', '14:00', '15:00', '20:00'],
  ['2026-07-15T12:00:00Z', '13:00', '15:00', '15:00', '20:00'],
])('uses local timezones and seasonal offsets at %s', (date, london, kyiv, moscow, beijing) => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(date));
  render(<WorldClocks />);
  const panel = screen.getByRole('region', { name: 'World clocks' });
  for (const [city, time] of [
    ['London', london],
    ['Kyiv', kyiv],
    ['Moscow', moscow],
    ['Beijing', beijing],
  ]) {
    const cell = within(panel).getByText(city ?? '').parentElement;
    expect(cell).toHaveTextContent(time ?? '');
  }
  expect(Array.from(panel.querySelectorAll('dt'), (item) => item.textContent)).toEqual([
    'London',
    'Kyiv',
    'Moscow',
    'Beijing',
  ]);
  expect(panel.querySelectorAll('time')).toHaveLength(4);
});
