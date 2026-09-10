import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { SelectedEventFacts } from './SelectedEventFacts';
import { EventInspector } from './EventInspector';

it('shows readable facts first and keeps all original source fields available on demand', async () => {
  const user = userEvent.setup();
  const event = liveEvent({
    attributes: { magnitude: 4.2, depth_km: 10, custom_field: '<img src=x onerror=alert(1)>' },
    severity: 0.5,
  });
  const { rerender } = render(<EventInspector event={event} onClose={vi.fn()} />, {
    wrapper: MemoryRouter,
  });
  const facts = screen.getByRole('region', { name: 'Earthquake details' });
  expect(within(facts).getByText('10 km')).toBeVisible();
  expect(screen.getByText('custom_field')).not.toBeVisible();
  expect(screen.getByText('0.50 / 1')).toBeVisible();
  expect(screen.queryByText('50%')).not.toBeInTheDocument();
  expect(screen.getByText(/not accuracy or likelihood/)).toBeVisible();
  await user.click(screen.getByText('Source fields'));
  expect(screen.getByText('custom_field')).toBeVisible();
  expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeVisible();
  expect(document.querySelector('img')).toBeNull();
  expect(screen.getByRole('link', { name: 'Research this' })).toBeVisible();
  expect(screen.getByRole('link', { name: 'Open source' })).toHaveAttribute(
    'rel',
    'noopener noreferrer',
  );

  rerender(<EventInspector event={{ ...event, id: 'another-event' }} onClose={vi.fn()} />);
  expect(screen.getByText('custom_field')).not.toBeVisible();
});

it('renders provider strings as text and remains absent for unrelated reports', () => {
  const { rerender } = render(
    <SelectedEventFacts
      event={liveEvent({
        category: 'aviation',
        subtype: 'aircraft',
        attributes: { registration: '<script>bad()</script>' },
      })}
    />,
  );
  expect(screen.getByText('<script>bad()</script>')).toBeVisible();
  expect(document.querySelector('script')).toBeNull();
  rerender(<SelectedEventFacts event={liveEvent({ category: 'news', subtype: 'article' })} />);
  expect(screen.queryByRole('region')).not.toBeInTheDocument();
});
