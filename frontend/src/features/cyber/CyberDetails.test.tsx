import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import { cyberActors, cyberBriefing, cyberItems, cyberSnapshot } from '@/test/fixtures.cyber';
import { ApiError } from '@/lib/api/errors';
import { CyberActivity } from './CyberActivity';
import { CyberActors } from './CyberActors';
import { CyberCharts } from './CyberCharts';
import { CyberKpis } from './CyberKpis';
import { CyberVulnerabilities } from './CyberVulnerabilities';
import { CyberBriefing } from './CyberBriefing';
import { cyberCountry, filterCyberItems } from './cyberPresentation';

it('explains empty observations and exposes the underlying chart counts', async () => {
  const user = userEvent.setup();
  const data = cyberSnapshot();
  data.retained_count = 0;
  data.counts = data.counts.map((row) => ({ ...row, count: 0 }));
  data.timeline = [];
  data.actor_mentions = [];
  data.top_countries = [];
  data.sources = [];
  render(<CyberKpis data={data} />);
  expect(screen.getByRole('list', { name: 'Cyber reporting headline figures' })).toBeVisible();
  render(<CyberCharts data={data} onCountry={vi.fn()} />);
  expect(screen.getByText(/No records to apportion/)).toBeVisible();
  expect(screen.getByText(/Locations are not established/)).toBeVisible();
  expect(screen.getByText(/No source returned dated records/)).toBeVisible();
  await user.click(screen.getByText('Table view'));
  expect(
    screen.getByRole('table', { name: 'Daily cyber reporting volume, as a table' }),
  ).toBeVisible();
});
it('lets a country bar narrow the activity list and marks alliance members', async () => {
  const user = userEvent.setup();
  const onCountry = vi.fn();
  render(<CyberCharts data={cyberSnapshot()} onCountry={onCountry} />);
  const countries = within(
    screen.getByRole('list', { name: 'Records by source-supplied country' }),
  );
  expect(countries.getByText('NATO member')).toBeVisible();
  await user.click(countries.getByRole('button', { name: /United Kingdom/ }));
  expect(onCountry).toHaveBeenCalledWith('GB');
  const nato = within(
    screen.getByRole('list', { name: 'Records with country context in NATO member states' }),
  );
  expect(nato.getAllByRole('listitem')).toHaveLength(1);
});
it('bounds the initially rendered activity list and lets the operator reveal more', async () => {
  const user = userEvent.setup();
  const items = Array.from({ length: 31 }, (_, i) => ({ ...cyberItems[0]!, id: String(i) }));
  const onTheme = vi.fn();
  render(
    <MemoryRouter>
      <CyberActivity items={items} days={2} onActor={vi.fn()} onTheme={onTheme} />
    </MemoryRouter>,
  );
  expect(screen.getAllByRole('heading')).toHaveLength(30);
  await user.click(screen.getByRole('button', { name: 'Show more reports (1 remaining)' }));
  expect(screen.getAllByRole('heading')).toHaveLength(31);
  await user.click(screen.getAllByRole('button', { name: 'Nation-state' })[0]!);
  expect(onTheme).toHaveBeenCalledWith('nation_state');
});
it('shows no-matching-reference state and paginates the actor directory', async () => {
  const user = userEvent.setup();
  const data = structuredClone(cyberActors);
  data.catalogue!.actors = Array.from({ length: 25 }, (_, i) => ({
    ...data.catalogue!.actors[1]!,
    group_id: `G${String(i).padStart(4, '0')}`,
    name: `Reference ${i}`,
  }));
  render(
    <MemoryRouter>
      <CyberActors
        data={data}
        items={[]}
        mentions={[]}
        activityStatus="ready"
        selectedId="G0001"
        onSelect={vi.fn()}
        onActivity={vi.fn()}
      />
    </MemoryRouter>,
  );
  expect(screen.getByText(/does not establish inactivity/)).toBeVisible();
  expect(screen.getByText('Profile association: North Korea')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Show more actors' }));
  expect(screen.queryByRole('button', { name: 'Show more actors' })).not.toBeInTheDocument();
  await user.type(screen.getByRole('searchbox'), 'not present');
  expect(screen.getByText(/No reference profiles match/)).toBeVisible();
});
it('renders empty and missing-action vulnerability states accurately', () => {
  const { rerender } = render(<CyberVulnerabilities items={[]} />);
  expect(screen.getByText(/No KEV additions match/)).toBeVisible();
  const item = structuredClone(cyberItems[3]!);
  item.kev!.required_action = '';
  item.kev!.ransomware_use = '';
  item.kev!.due_date = '';
  item.summary = null;
  rerender(<CyberVulnerabilities items={[item]} />);
  expect(screen.getByText(/Read the linked CISA record/)).toBeVisible();
  expect(screen.getByText('Ransomware use: Not specified')).toBeVisible();
});
it('retains loading, error retry and active progress states without a fabricated assessment', async () => {
  const user = userEvent.setup();
  const retry = vi.fn();
  const state = {
    briefing: null,
    report: null,
    error: new ApiError(503, 'unavailable', 'AI temporarily unavailable'),
    loading: true,
    retry,
  };
  const { rerender } = render(
    <MemoryRouter>
      <CyberBriefing days={2} state={state} />
    </MemoryRouter>,
  );
  expect(screen.getByText('Loading your cyber briefing')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Retry cyber briefing' }));
  expect(retry).toHaveBeenCalledOnce();
  const response = cyberBriefing();
  response.job.status = 'running';
  response.job.total_sections = 4;
  response.job.completed_sections = 1;
  rerender(
    <MemoryRouter>
      <CyberBriefing
        days={2}
        state={{ ...state, error: null, loading: false, briefing: response }}
      />
    </MemoryRouter>,
  );
  expect(
    screen.getByRole('progressbar', { name: 'Cyber briefing sections completed' }),
  ).toHaveAttribute('value', '1');
  expect(screen.queryByRole('article', { name: 'Cyber briefing summary' })).not.toBeInTheDocument();
});
it('filters on actor membership, lens and CVE/product metadata without mistaking publisher country for geography', () => {
  expect(filterCyberItems(cyberItems, '', 'all', '', 'G0016').map((item) => item.id)).toEqual([
    'advisory-1',
  ]);
  expect(filterCyberItems(cyberItems, 'CVE-2026-12345', 'all', '', '')).toHaveLength(1);
  expect(filterCyberItems(cyberItems, 'APT29', 'all', 'GB', '')).toHaveLength(0);
  expect(filterCyberItems(cyberItems, '', 'all', '', '', 'ukraine').map((item) => item.id)).toEqual(
    ['outage-1'],
  );
  expect(cyberCountry(null)).toBe('Location not established');
  expect(cyberCountry('invalid-region')).toBe('invalid-region');
});
