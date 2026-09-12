import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { report } from '@/test/fixtures';
import { cyberActors, cyberBriefing, cyberSnapshot } from '@/test/fixtures.cyber';
import { parseCyberDays } from '@/lib/api/cyber';
import { useEventsStore } from '@/stores/events';

beforeEach(() =>
  server.use(
    http.get('/api/cyber', ({ request }) =>
      HttpResponse.json(
        cyberSnapshot(parseCyberDays(new URL(request.url).searchParams.get('days'))),
      ),
    ),
    http.get('/api/cyber/actors', () => HttpResponse.json(cyberActors)),
    http.post('/api/cyber/briefing', ({ request }) =>
      HttpResponse.json(
        cyberBriefing(parseCyberDays(new URL(request.url).searchParams.get('days'))),
      ),
    ),
  ),
);

it('opens a dedicated cyber workspace with attributed activity, timeline and source coverage', async () => {
  renderApp('/cyber', 'user');
  expect(await screen.findByRole('heading', { name: 'Cyber threat intelligence' })).toBeVisible();
  expect(await screen.findByRole('img', { name: 'Daily cyber reporting volume' })).toBeVisible();
  expect(
    within(screen.getByRole('navigation', { name: 'Primary' })).getByRole('link', {
      name: 'Cyber intelligence',
    }),
  ).toHaveAttribute('aria-current', 'page');
  const activity = within(screen.getByRole('list', { name: 'Cyber activity reports' }));
  expect(activity.getAllByRole('listitem')).toHaveLength(4);
  expect(activity.getByText(/not proof of malicious activity/)).toBeVisible();
  expect(activity.getByText(/criminal group’s claim/)).toBeVisible();
  expect(screen.getByText(/Source coverage/)).toHaveTextContent('1/2');
});

it('filters returned activity by kind, country and keyword and restores it', async () => {
  const { user } = renderApp('/cyber', 'user');
  await screen.findByRole('list', { name: 'Cyber activity reports' });
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Evidence type' }),
    'ransomware_claim',
  );
  expect(screen.getByRole('list', { name: 'Cyber activity reports' })).toHaveTextContent(
    'Example Manufacturing',
  );
  await user.selectOptions(screen.getByRole('combobox', { name: 'Country context' }), 'UA');
  expect(screen.getByText(/No records match/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Clear filters' }));
  await user.type(screen.getByRole('searchbox', { name: 'Search returned reports' }), 'APT29');
  expect(
    within(screen.getByRole('list', { name: 'Cyber activity reports' })).getAllByRole('listitem'),
  ).toHaveLength(1);
});

it('separates source-referenced historical actor profiles from matched current reporting', async () => {
  const { user } = renderApp('/cyber', 'user');
  await screen.findByRole('list', { name: 'Cyber activity reports' });
  await user.click(
    within(screen.getByRole('navigation', { name: 'Cyber workspace sections' })).getByRole(
      'button',
      { name: 'Threat actors' },
    ),
  );
  await user.type(
    screen.getByRole('searchbox', { name: /Search name, associated name/ }),
    'Midnight Blizzard',
  );
  await user.click(screen.getByRole('button', { name: /View APT29/ }));
  const inspector = within(screen.getByRole('complementary', { name: 'Selected threat actor' }));
  expect(inspector.getByRole('heading', { name: 'APT29' })).toBeVisible();
  expect(inspector.getByText(/not a verified identity crosswalk/)).toBeVisible();
  expect(inspector.getByRole('link', { name: /Read profile/ })).toHaveAttribute(
    'href',
    'https://attack.mitre.org/groups/G0016/',
  );
  await user.click(inspector.getByRole('button', { name: 'Filter activity by this actor' }));
  expect(screen.getByText(/Actor mentions: APT29/)).toBeVisible();
  expect(
    within(screen.getByRole('list', { name: 'Cyber activity reports' })).getAllByRole('listitem'),
  ).toHaveLength(1);
});

it('shows exploitation context, mitigation and scoped dates without inventing incident geography', async () => {
  const { user } = renderApp('/cyber', 'user');
  await screen.findByRole('list', { name: 'Cyber activity reports' });
  await user.click(
    within(screen.getByRole('navigation', { name: 'Cyber workspace sections' })).getByRole(
      'button',
      { name: 'Exploited vulnerabilities' },
    ),
  );
  expect(screen.getByText('Apply the vendor update and review exposed services.')).toBeVisible();
  expect(screen.getByText(/not a universal deadline/)).toBeVisible();
  expect(screen.queryByRole('button', { name: /View country context/ })).not.toBeInTheDocument();
});

it('uses all four periods while filters and refresh never admit another briefing', async () => {
  const starts = vi.fn();
  server.use(
    http.post('/api/cyber/briefing', ({ request }) => {
      const days = parseCyberDays(new URL(request.url).searchParams.get('days'));
      starts(days);
      return HttpResponse.json(cyberBriefing(days));
    }),
  );
  const { user, router } = renderApp('/cyber', 'user');
  await screen.findByRole('list', { name: 'Cyber activity reports' });
  await user.selectOptions(screen.getByRole('combobox', { name: 'Country context' }), 'GB');
  await user.click(screen.getByRole('button', { name: 'Refresh sources' }));
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Refresh sources' })).not.toBeDisabled(),
  );
  expect(starts).toHaveBeenCalledTimes(1);
  for (const days of [5, 7, 14]) {
    await user.click(screen.getByRole('button', { name: `${days} Day` }));
    await waitFor(() => expect(starts).toHaveBeenLastCalledWith(days));
    await screen.findByRole('list', { name: 'Cyber activity reports' });
    expect(router.state.location.search).toContain(`days=${days}`);
  }
  expect(starts).toHaveBeenCalledTimes(4);
});

it('keeps report dates and export links, then hides the previous report when switching period', async () => {
  let release: () => void = () => {
    throw new Error('Not initialised');
  };
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.post('/api/cyber/briefing', async ({ request }) => {
      const days = parseCyberDays(new URL(request.url).searchParams.get('days'));
      const response = cyberBriefing(days);
      if (days === 5) await gate;
      if (days === 2) {
        response.job.status = 'completed';
        response.job.report_id = report.report.id;
      }
      return HttpResponse.json(response);
    }),
  );
  const { user } = renderApp('/cyber', 'user');
  await user.click(await screen.findByRole('button', { name: 'Intelligence briefing' }));
  expect(await screen.findByRole('article', { name: 'Cyber briefing summary' })).toBeVisible();
  expect(screen.getByRole('link', { name: 'Read full briefing and export' })).toHaveAttribute(
    'href',
    `/reports/${report.report.id}`,
  );
  await user.click(screen.getByRole('button', { name: '5 Day' }));
  expect(screen.queryByRole('article', { name: 'Cyber briefing summary' })).not.toBeInTheDocument();
  await act(async () => {
    release();
    await gate;
  });
  expect(await screen.findByText(/Reporting period:/)).toHaveTextContent('7 Sept 2026');
});

it('opens explicitly labelled country context and enables only the requested map category', async () => {
  const { user, router } = renderApp('/cyber', 'user');
  await screen.findByRole('list', { name: 'Cyber activity reports' });
  await user.selectOptions(screen.getByRole('combobox', { name: 'Country context' }), 'GB');
  await user.click(screen.getByRole('button', { name: 'Open cyber map' }));
  await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  expect(useEventsStore.getState().hidden.includes('cyber')).toBe(false);
  expect(useEventsStore.getState().hidden.includes('aviation')).toBe(true);
});

it('handles unavailable sources and disabled actor reference without replacing gaps with data', async () => {
  server.use(
    http.get('/api/cyber', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'Cyber source snapshot unavailable' } },
        { status: 503 },
      ),
    ),
    http.get('/api/cyber/actors', () =>
      HttpResponse.json({
        available: false,
        catalogue: null,
        coverage_note: 'Actor reference is disabled.',
      }),
    ),
  );
  const { user } = renderApp('/cyber', 'user');
  expect(await screen.findByText('Cyber source snapshot unavailable')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Threat actors' }));
  expect(await screen.findByText('Actor reference is disabled.')).toBeVisible();
  expect(screen.queryByText('APT29')).not.toBeInTheDocument();
});

it('keeps actor references useful without reporting zero activity when the snapshot fails', async () => {
  server.use(
    http.get('/api/cyber', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'Cyber source snapshot unavailable' } },
        { status: 503 },
      ),
    ),
  );
  const { user } = renderApp('/cyber', 'user');
  await screen.findByText('Cyber source snapshot unavailable');
  await user.click(screen.getByRole('button', { name: 'Threat actors' }));
  await user.click(
    await screen.findByRole('button', { name: /View APT29 .*Activity unavailable/ }),
  );
  expect(screen.getByText(/Activity unavailable\. Mention counts/)).toBeVisible();
  expect(screen.queryByText(/Matched records: 0/)).not.toBeInTheDocument();
  expect(
    screen.getByRole('link', { name: 'Read profile and original references on MITRE ATT&CK' }),
  ).toBeVisible();
});

it('hides previous actor counts while the selected reporting period is loading', async () => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get('/api/cyber', async ({ request }) => {
      const days = parseCyberDays(new URL(request.url).searchParams.get('days'));
      if (days === 14) await gate;
      return HttpResponse.json(cyberSnapshot(days));
    }),
  );
  const { user } = renderApp('/cyber', 'user');
  await screen.findByRole('list', { name: 'Cyber activity reports' });
  await user.click(screen.getByRole('button', { name: 'Threat actors' }));
  await user.click(await screen.findByRole('button', { name: /View APT29 .*1 mentions/ }));
  await user.click(screen.getByRole('button', { name: '14 Day' }));
  expect(screen.getByText(/Activity loading\. Mention counts/)).toBeVisible();
  expect(screen.queryByText(/Matched records:/)).not.toBeInTheDocument();
  await act(async () => {
    release();
    await gate;
  });
  expect(await screen.findByText(/Matched records: 1\./)).toBeVisible();
});
