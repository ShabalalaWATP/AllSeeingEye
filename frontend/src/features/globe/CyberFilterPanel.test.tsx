import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { useEventsStore } from '@/stores/events';
import { useCyberFiltersStore } from '@/stores/cyberFilters';
import { CyberFilterPanel } from './CyberFilterPanel';

it('shares type and search choices, reports snapshot limits, and blocks record picks during drawing', async () => {
  applySession('user');
  useEventsStore.setState({ hidden: [], country: 'GB' });
  const select = vi.fn();
  const refresh = vi.fn();
  const cyber = {
    events: Array.from({ length: 30 }, (_, index) =>
      liveEvent({
        id: String(index),
        title: `Claim ${index}`,
        category: 'cyber',
        subtype: 'ransomware',
        geo_confidence: 'country',
        point: null,
      }),
    ),
    groups: [],
    selected: null,
    close: vi.fn(),
    select: vi.fn(),
    refresh,
    loading: false,
    fetchedAt: '2026-09-12T12:00:00Z',
    error: null,
    limited: true,
  };
  const { rerender } = render(
    <MemoryRouter>
      <CyberFilterPanel cyber={cyber} onSelect={select} picking />
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  expect(screen.getByText(/Nation: GB/)).toBeVisible();
  expect(screen.getByText(/snapshot reached its limit/)).toBeVisible();
  expect(screen.queryByRole('button', { name: /Claim 25 / })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Claim 0 / })).toBeDisabled();
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Record type' }),
    'known_exploited_vulnerability',
  );
  expect(useCyberFiltersStore.getState().kind).toBe('known_exploited_vulnerability');
  await user.type(screen.getByRole('searchbox', { name: 'Search cyber records' }), 'CVE-2026');
  expect(useCyberFiltersStore.getState().query).toBe('CVE-2026');
  await user.click(screen.getByRole('button', { name: 'Refresh cyber records' }));
  expect(refresh).toHaveBeenCalledOnce();
  rerender(
    <MemoryRouter>
      <CyberFilterPanel cyber={cyber} onSelect={select} picking={false} />
    </MemoryRouter>,
  );
  await user.click(screen.getByRole('button', { name: /Claim 0 / }));
  expect(select).toHaveBeenCalledWith(cyber.events[0]);
  rerender(
    <MemoryRouter>
      <CyberFilterPanel
        cyber={{ ...cyber, events: [], error: 'Unavailable', limited: false }}
        onSelect={select}
        picking={false}
      />
    </MemoryRouter>,
  );
  expect(screen.getByRole('alert')).toHaveTextContent('Unavailable');
  expect(screen.getByText('No matching records in this collected snapshot.')).toBeVisible();
});
