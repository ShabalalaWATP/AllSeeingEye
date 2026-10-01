import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { mockMatchMedia } from '@/test/env';
import { liveEvent } from '@/test/fixtures';

import { ReplayBanner } from './ReplayBanner';
import { ReplayControls } from './ReplayControls';
import { REPLAY_TICK_MS, useLiveReplay } from './useLiveReplay';
import { useReplayStore } from './replayStore';

const HOUR = 3_600_000;
const base = Date.UTC(2026, 8, 30, 0, 0);
const at = (hours: number) => new Date(base + hours * HOUR).toISOString();

const events = [
  liveEvent({ id: 'first', published_at: at(0) }),
  liveEvent({ id: 'second', published_at: at(1) }),
  liveEvent({ id: 'third', published_at: at(2) }),
  liveEvent({ id: 'undated', published_at: null }),
];

function Harness({ items }: { items: LiveEvent[] }) {
  const replay = useLiveReplay(items);
  return (
    <>
      <ReplayBanner />
      <ReplayControls replay={replay} />
      <output data-testid="shown">{replay.events.map((event) => event.id).join(',')}</output>
    </>
  );
}

const NOTICE = '.map-tool-notice';
const shown = () => screen.getByTestId('shown').textContent;
const announcer = () => screen.getByTestId('replay-announcer');

describe('live replay controls', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    useReplayStore.getState().returnToLive();
    useReplayStore.setState({ announcement: '' });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('stays live until replay starts and states what replay covers', () => {
    render(<Harness items={events} />);
    expect(shown()).toBe('first,second,third,undated');
    expect(screen.queryByRole('region', { name: 'Replay mode' })).not.toBeInTheDocument();
    expect(screen.getByText(/only the events this browser already holds/)).toBeVisible();
    expect(screen.getByText(/at most 5,000/)).toBeVisible();
    expect(
      screen.getByText('1 event without a usable time is excluded from replay.'),
    ).toBeVisible();
  });

  it('scrubs and steps hour by hour without any network request', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const user = userEvent.setup();
    render(<Harness items={events} />);
    await user.click(screen.getByRole('button', { name: 'Start replay' }));

    const banner = screen.getByRole('region', { name: 'Replay mode' });
    expect(within(banner).getByText('Replay, not live')).toBeVisible();
    expect(within(banner).getByText(/30 Sep\w* 2026, 00:00 UTC/)).toBeVisible();
    expect(shown()).toBe('first');
    expect(announcer()).toHaveTextContent(/Replay started at 30 Sep\w* 2026, 00:00 UTC/);

    await user.click(screen.getByRole('button', { name: 'Step forward one hour' }));
    expect(shown()).toBe('first,second');

    const slider = screen.getByRole('slider', { name: 'Replay time' });
    expect(slider).toHaveAttribute('aria-valuetext', expect.stringMatching(/01:00 UTC/));
    fireEvent.change(slider, { target: { value: '2' } });
    expect(shown()).toBe('first,second,third');
    expect(screen.getByText(/Newest retained event reached/, { selector: NOTICE })).toBeVisible();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('stops at the retention boundary with a message', async () => {
    const user = userEvent.setup();
    render(<Harness items={events} />);
    await user.click(screen.getByRole('button', { name: 'Start replay' }));
    await user.click(screen.getByRole('button', { name: 'Step back one hour' }));
    expect(shown()).toBe('first');
    expect(screen.getByText(/Start of the retained window/, { selector: NOTICE })).toBeVisible();
    expect(announcer()).toHaveTextContent(/Start of the retained window/);
  });

  it('plays to the newest event, then pauses with one announcement', () => {
    vi.useFakeTimers();
    render(<Harness items={events} />);
    fireEvent.click(screen.getByRole('button', { name: 'Start replay' }));
    fireEvent.click(screen.getByRole('button', { name: 'Play replay' }));
    expect(announcer()).toHaveTextContent('Replay playing.');
    act(() => {
      vi.advanceTimersByTime(REPLAY_TICK_MS);
    });
    expect(shown()).toBe('first,second');
    // Playback ticks do not flood the polite announcer.
    expect(announcer()).toHaveTextContent('Replay playing.');
    act(() => {
      vi.advanceTimersByTime(REPLAY_TICK_MS * 3);
    });
    expect(shown()).toBe('first,second,third');
    expect(screen.getByRole('button', { name: 'Play replay' })).toBeVisible();
    expect(announcer()).toHaveTextContent(/Newest retained event reached/);
  });

  it('disables automatic play when reduced motion is requested', async () => {
    mockMatchMedia(true);
    const user = userEvent.setup();
    render(<Harness items={events} />);
    await user.click(screen.getByRole('button', { name: 'Start replay' }));
    expect(screen.getByRole('button', { name: 'Play replay' })).toBeDisabled();
    expect(screen.getByText(/Automatic play is off because reduced motion/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Step forward one hour' }));
    expect(shown()).toBe('first,second');
  });

  it('returns to live from the map banner', async () => {
    const user = userEvent.setup();
    render(<Harness items={events} />);
    await user.click(screen.getByRole('button', { name: 'Start replay' }));
    const banner = screen.getByRole('region', { name: 'Replay mode' });
    await user.click(within(banner).getByRole('button', { name: 'Return to live' }));
    expect(screen.queryByRole('region', { name: 'Replay mode' })).not.toBeInTheDocument();
    expect(shown()).toBe('first,second,third,undated');
    expect(announcer()).toHaveTextContent('Returned to live events.');
  });

  it('cannot start without a usable time', () => {
    render(<Harness items={[liveEvent({ published_at: null })]} />);
    expect(screen.getByRole('button', { name: 'Start replay' })).toBeDisabled();
    expect(screen.getByText('No retained event has a usable time to replay.')).toBeVisible();
  });

  it('returns the map to live when it unmounts', async () => {
    const user = userEvent.setup();
    const view = render(<Harness items={events} />);
    await user.click(screen.getByRole('button', { name: 'Start replay' }));
    expect(useReplayStore.getState().active).toBe(true);
    view.unmount();
    expect(useReplayStore.getState()).toMatchObject({ active: false, playing: false });
  });
});
