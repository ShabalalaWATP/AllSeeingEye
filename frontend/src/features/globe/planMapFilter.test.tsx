import { act, render, renderHook, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { PlanMapMatches } from '@/lib/api/direction';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';
import { usePlanMapFilterStore } from '@/stores/planMapFilter';
import { liveEvent, plan } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { PlanFilterPanel } from './PlanFilterPanel';
import { PlanMatchFacts } from './PlanMatchFacts';
import { PLAN_MATCH_REFRESH_MS, usePlanMapFilter } from './usePlanMapFilter';
import { useDashboardEvents } from './useDashboardEvents';

const now = Date.parse('2026-09-10T12:00:00Z');
const shelling = liveEvent({
  id: 'shelling',
  country_iso: 'UA',
  published_at: '2026-09-10T11:00:00Z',
});
const talks = liveEvent({ id: 'talks', country_iso: 'PL', published_at: '2026-09-10T11:10:00Z' });
const quake = liveEvent({ id: 'quake', country_iso: 'DE', published_at: '2026-09-10T11:20:00Z' });

function matches(overrides: Partial<PlanMapMatches> = {}): PlanMapMatches {
  return {
    plan,
    window_hours: 168,
    pool_limit: 5000,
    per_requirement_limit: 30,
    considered: 42,
    truncated: false,
    matches: [
      { event_id: 'shelling', codes: ['SIR-1.1', 'SIR-1.2'] },
      { event_id: 'talks', codes: ['SIR-1.2'] },
      { event_id: 'expired', codes: ['SIR-1.1'] },
    ],
    ...overrides,
  };
}

function serveMatches(reply: () => Response | Promise<Response>) {
  const calls: string[] = [];
  server.use(
    http.get('/api/direction/plans/:id/map-matches', ({ params }) => {
      calls.push(String(params.id));
      return reply();
    }),
  );
  return calls;
}

beforeEach(() => {
  applySession('user');
  usePlanMapFilterStore.getState().reset();
  useEventsStore.setState({ hidden: [], country: null });
  useEventsStore.getState().applyUpsert([shelling, talks, quake]);
});

afterEach(() => {
  vi.useRealTimers();
  usePlanMapFilterStore.getState().reset();
});

describe('collection plan map filter', () => {
  it('intersects plan matches with the other map filters and clears only itself', async () => {
    serveMatches(() => HttpResponse.json(matches()));
    const { result } = renderHook(() => useDashboardEvents(now));
    expect(result.current.quality.filtered.map((event) => event.id).sort()).toEqual([
      'quake',
      'shelling',
      'talks',
    ]);
    act(() => usePlanMapFilterStore.getState().select(plan.id));
    expect(result.current.quality.filtered).toEqual([]);
    await waitFor(() =>
      expect(result.current.quality.filtered.map((event) => event.id).sort()).toEqual([
        'shelling',
        'talks',
      ]),
    );
    act(() => result.current.setCountry('UA'));
    expect(result.current.quality.filtered.map((event) => event.id)).toEqual(['shelling']);
    act(() => usePlanMapFilterStore.getState().select(null));
    expect(result.current.quality.filtered.map((event) => event.id)).toEqual(['shelling']);
    expect(useEventsStore.getState().country).toBe('UA');
  });

  it('refreshes at most once a minute with one request in flight, and stops when cleared', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const calls = serveMatches(() => HttpResponse.json(matches()));
    renderHook(() => useDashboardEvents(now));
    act(() => usePlanMapFilterStore.getState().select(plan.id));
    await waitFor(() => expect(usePlanMapFilterStore.getState().status).toBe('ready'));
    expect(calls).toHaveLength(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(PLAN_MATCH_REFRESH_MS - 1_000);
    });
    expect(calls).toHaveLength(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    await waitFor(() => expect(calls).toHaveLength(2));
    act(() => usePlanMapFilterStore.getState().select(null));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(PLAN_MATCH_REFRESH_MS * 3);
    });
    expect(calls).toHaveLength(2);
  });

  it('updates labels after a plan edit and drops events that left the live store', async () => {
    let name = plan.name;
    serveMatches(() => HttpResponse.json(matches({ plan: { ...plan, name } })));
    const { result } = renderHook(() => useDashboardEvents(now));
    act(() => usePlanMapFilterStore.getState().select(plan.id));
    await waitFor(() => expect(result.current.quality.filtered).toHaveLength(2));
    act(() => useEventsStore.getState().applyExpire(['talks']));
    expect(result.current.quality.filtered.map((event) => event.id)).toEqual(['shelling']);
    name = 'Renamed plan';
    act(() => usePlanMapFilterStore.getState().refresh());
    await waitFor(() =>
      expect(usePlanMapFilterStore.getState().result?.plan.name).toBe('Renamed plan'),
    );
  });

  it('clears the selection and private results on access or account changes', async () => {
    serveMatches(() => HttpResponse.json(matches()));
    const { result } = renderHook(() => useDashboardEvents(now));
    act(() => usePlanMapFilterStore.getState().select(plan.id));
    await waitFor(() => expect(usePlanMapFilterStore.getState().codes).not.toBeNull());
    act(() => invalidateWorkspaceAccess());
    expect(usePlanMapFilterStore.getState()).toMatchObject({
      planId: null,
      codes: null,
      result: null,
    });
    expect(result.current.quality.filtered).toHaveLength(3);
    act(() => usePlanMapFilterStore.getState().select(plan.id));
    await waitFor(() => expect(usePlanMapFilterStore.getState().codes).not.toBeNull());
    act(() => useAuthStore.getState().clearSession());
    expect(usePlanMapFilterStore.getState()).toMatchObject({
      planId: null,
      codes: null,
      result: null,
    });
  });

  it('discards a late response that belongs to an earlier selection', () => {
    const store = usePlanMapFilterStore.getState();
    store.select(plan.id);
    store.select(null);
    store.succeed(plan.id, matches(), now);
    expect(usePlanMapFilterStore.getState().codes).toBeNull();
  });
});

/** The map mounts the loader through its event pipeline; the panel only chooses and reports. */
function Harness() {
  usePlanMapFilter([]);
  return <PlanFilterPanel shown={2} />;
}

describe('plan filter panel', () => {
  async function choose() {
    const user = userEvent.setup();
    render(<Harness />);
    await user.selectOptions(await screen.findByLabelText('Collection plan'), plan.id);
    return user;
  }

  it('offers only the readable plans the server lists and explains the sample', async () => {
    serveMatches(() => HttpResponse.json(matches({ truncated: true })));
    const user = await choose();
    expect(screen.getAllByRole('option').map((option) => option.textContent)).toEqual([
      'No plan filter',
      plan.name,
    ]);
    expect(await screen.findByText(/3 events match Kharkiv axis; 2 pass/)).toBeInTheDocument();
    expect(screen.getByText(/the last 168 hours, 42 events considered/)).toBeInTheDocument();
    expect(screen.getByText(/up to 5,000 per query and 30 per requirement/)).toBeInTheDocument();
    expect(screen.getByText(/sample reached its limit/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Clear plan filter' }));
    expect(usePlanMapFilterStore.getState().planId).toBeNull();
  });

  it('distinguishes no matches, unavailable, failure and lost access', async () => {
    let reply: () => Response = () => HttpResponse.json(matches({ matches: [] }));
    serveMatches(() => reply());
    const user = await choose();
    expect(await screen.findByText(/No events from the last 168 hours match/)).toBeInTheDocument();
    reply = () =>
      HttpResponse.json(
        { error: { code: 'invalid_request', message: 'The linked area is unavailable.' } },
        { status: 422 },
      );
    await user.click(screen.getByRole('button', { name: 'Refresh matches' }));
    expect(await screen.findByText(/Plan matches are unavailable/)).toBeInTheDocument();
    expect(screen.getByText(/keeps the last matches/)).toBeInTheDocument();
    reply = () => HttpResponse.error();
    await user.click(screen.getByRole('button', { name: 'Refresh matches' }));
    expect(await screen.findByText(/Plan matches could not be loaded/)).toBeInTheDocument();
    reply = () =>
      HttpResponse.json({ error: { code: 'not_found', message: 'Gone.' } }, { status: 404 });
    await user.click(screen.getByRole('button', { name: 'Refresh matches' }));
    expect(await screen.findByText(/no longer available to you/)).toBeInTheDocument();
    expect(usePlanMapFilterStore.getState()).toMatchObject({ planId: null, codes: null });
    expect(screen.getByLabelText('Collection plan')).toHaveValue('');
  });

  it('shows the loading state before the first sample arrives', async () => {
    let release: () => void = () => undefined;
    serveMatches(
      () =>
        new Promise<Response>((resolve) => {
          release = () => resolve(HttpResponse.json(matches()));
        }),
    );
    await choose();
    expect(await screen.findByText('Finding plan matches')).toBeInTheDocument();
    act(() => release());
    expect(await screen.findByText(/3 events match/)).toBeInTheDocument();
  });
});

it('lists every matched SIR code with its text in the event inspector', () => {
  usePlanMapFilterStore.getState().select(plan.id);
  usePlanMapFilterStore.getState().succeed(plan.id, matches(), now);
  render(<PlanMatchFacts eventId="shelling" />);
  const facts = screen.getByRole('region', { name: 'Plan matches' });
  expect(within(facts).getByText('SIR-1.1')).toBeInTheDocument();
  expect(within(facts).getByText('SIR-1.2')).toBeInTheDocument();
  expect(within(facts).getByText('Talks or ceasefire moves')).toBeInTheDocument();
  render(<PlanMatchFacts eventId="quake" />);
  expect(screen.getAllByRole('region', { name: 'Plan matches' })).toHaveLength(1);
});
