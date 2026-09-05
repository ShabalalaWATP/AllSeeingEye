import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { liveEvent, storeStats } from '@/test/fixtures';

import { EventInspector, isHttpUrl, sourceLabel } from './EventInspector';
import { LayerPanel, formatBudget } from './LayerPanel';
import { Ticker } from './Ticker';

const NOW = Date.UTC(2026, 8, 5, 3, 0, 0);

describe('LayerPanel', () => {
  it('lists every category with its count, reports the budget and toggles', async () => {
    const onToggle = vi.fn();
    const onWindow = vi.fn();
    const onToggleTerminator = vi.fn();
    const onToggleLite = vi.fn();
    render(
      <LayerPanel
        counts={{ disaster: 3 }}
        hidden={['cyber']}
        stats={storeStats}
        status="live"
        error={null}
        terminator
        lite={false}
        windowHours={null}
        onWindow={onWindow}
        onToggle={onToggle}
        onToggleTerminator={onToggleTerminator}
        onToggleLite={onToggleLite}
        interference={false}
        onToggleInterference={vi.fn()}
      />,
    );
    const switches = screen.getAllByRole('switch');
    expect(switches).toHaveLength(14);
    expect(screen.getByRole('switch', { name: 'Day and night on' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
    expect(screen.getByRole('switch', { name: 'Lite mode off' })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    await userEvent.click(screen.getByRole('switch', { name: 'Day and night on' }));
    expect(onToggleTerminator).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole('switch', { name: 'Lite mode off' }));
    expect(onToggleLite).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('switch', { name: 'Disasters 3' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
    expect(screen.getByRole('switch', { name: 'Cyber 0' })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    expect(screen.getByRole('status')).toHaveTextContent('Live');
    expect(screen.getByText('2 events, 0.0 of 1 MB')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('switch', { name: 'Cyber 0' }));
    expect(onToggle).toHaveBeenCalledWith('cyber');
  });

  it('shows the load error and no budget line before the first load', () => {
    render(
      <LayerPanel
        counts={{}}
        hidden={[]}
        stats={null}
        status="offline"
        error="Down."
        terminator={false}
        lite
        windowHours={24}
        onWindow={vi.fn()}
        onToggle={vi.fn()}
        onToggleTerminator={vi.fn()}
        onToggleLite={vi.fn()}
        interference={false}
        onToggleInterference={vi.fn()}
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Down.');
    expect(screen.queryByText(/events,/)).not.toBeInTheDocument();
    expect(
      formatBudget({ ...storeStats, estimated_bytes: 2_621_440, budget_bytes: 8_388_608 }),
    ).toBe('2 events, 2.5 of 8 MB');
  });
});

describe('EventInspector', () => {
  it('shows grade, provenance, summary, attributes, tags and a safe link', async () => {
    const onClose = vi.fn();
    render(
      <EventInspector
        event={liveEvent({
          title_en: 'Magnitude 4.2 near Somewhere',
          country_iso: 'GB',
          tags: ['seismic'],
          attributes: { magnitude: 4.2, depth_km: 10, note: '', flag: null },
        })}
        storySize={3}
        onClose={onClose}
      />,
    );
    const drawer = screen.getByRole('complementary', { name: 'Event details' });
    expect(
      within(drawer).getByRole('heading', { name: 'M4.2 near Somewhere' }),
    ).toBeInTheDocument();
    expect(within(drawer).getByText('Magnitude 4.2 near Somewhere')).toBeInTheDocument();
    expect(within(drawer).getByTitle('Instrument data')).toHaveTextContent('Grade A2');
    expect(within(drawer).getByText(/^Instrument data \(story of 3 items\)$/)).toBeInTheDocument();
    expect(within(drawer).getByText('usgs earthquakes')).toBeInTheDocument();
    expect(within(drawer).getByText('5 Sept 2026, 00:00 UTC')).toBeInTheDocument();
    expect(within(drawer).getByText('50.000, 10.000 (exact)')).toBeInTheDocument();
    expect(within(drawer).getByText('GB')).toBeInTheDocument();
    expect(within(drawer).getByText('50%')).toBeInTheDocument();
    expect(within(drawer).getByText('Depth 10 km.')).toBeInTheDocument();
    expect(within(drawer).getByText('depth_km')).toBeInTheDocument();
    expect(within(drawer).queryByText('note')).not.toBeInTheDocument();
    expect(within(drawer).queryByText('flag')).not.toBeInTheDocument();
    expect(within(drawer).getByText('seismic')).toBeInTheDocument();
    const link = within(drawer).getByRole('link', { name: 'Open source' });
    expect(link).toHaveAttribute('href', 'https://example.com/e1');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    await userEvent.click(within(drawer).getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('never renders a non-http link and skips absent fields', () => {
    render(
      <EventInspector
        event={liveEvent({
          url: 'javascript:alert(1)',
          summary: null,
          point: null,
          severity: null,
          tags: [],
          attributes: {},
        })}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.queryByText('Position')).not.toBeInTheDocument();
    expect(screen.queryByText('Severity')).not.toBeInTheDocument();
    expect(isHttpUrl('http://example.org/x')).toBe(true);
    expect(isHttpUrl('ftp://example.org/x')).toBe(false);
    expect(isHttpUrl('not a url')).toBe(false);
    expect(isHttpUrl(null)).toBe(false);
    expect(sourceLabel('nasa_eonet')).toBe('nasa eonet');
  });
});

describe('Ticker', () => {
  it('shows the newest events up to the limit with relative ages and selection', async () => {
    const onSelect = vi.fn();
    const events = [
      liveEvent({ id: 'a', title: 'Newest', published_at: '2026-09-05T02:58:00Z' }),
      liveEvent({ id: 'b', title: 'Older', published_at: '2026-09-04T00:00:00Z' }),
      liveEvent({ id: 'c', title: 'Hidden by limit' }),
    ];
    render(<Ticker events={events} selectedId="b" now={NOW} onSelect={onSelect} limit={2} />);
    const strip = screen.getByRole('navigation', { name: 'Latest events' });
    const buttons = within(strip).getAllByRole('button');
    expect(buttons).toHaveLength(2);
    expect(buttons[0]).toHaveTextContent('Newest');
    expect(buttons[0]).toHaveTextContent('2m ago');
    expect(buttons[0]).toHaveAttribute('aria-pressed', 'false');
    expect(buttons[1]).toHaveTextContent('1d ago');
    expect(buttons[1]).toHaveAttribute('aria-pressed', 'true');
    expect(within(strip).queryByText('Hidden by limit')).not.toBeInTheDocument();
    await userEvent.click(buttons[0]!);
    expect(onSelect).toHaveBeenCalledWith(events[0]);
  });

  it('explains when nothing has arrived yet', () => {
    render(<Ticker events={[]} selectedId={null} now={NOW} onSelect={vi.fn()} />);
    expect(screen.getByText('Waiting for events')).toBeInTheDocument();
  });
});
