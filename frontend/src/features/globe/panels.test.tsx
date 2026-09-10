import { fireEvent, render as renderUi, screen, within } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router';

import { userEvent } from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { liveEvent, storeStats } from '@/test/fixtures';

import { EventInspector, isHttpUrl, sourceLabel } from './EventInspector';
import { LayerPanel, formatBudget } from './LayerPanel';

const render = (ui: ReactElement) => renderUi(ui, { wrapper: MemoryRouter });

describe('EventInspector keyboard dismissal', () => {
  it('focuses its close action, dismisses on Escape and restores the opening control', async () => {
    const user = userEvent.setup();
    const opener = document.createElement('button');
    document.body.append(opener);
    opener.focus();
    const onClose = vi.fn();
    const { unmount } = render(<EventInspector event={liveEvent()} onClose={onClose} />);
    expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledOnce();
    unmount();
    expect(opener).toHaveFocus();
    opener.remove();
  });

  it('leaves Escape inside a modal or an editable field to that control', () => {
    const onClose = vi.fn();
    render(<EventInspector event={liveEvent()} onClose={onClose} />);
    const dialog = document.createElement('dialog');
    dialog.open = true;
    const button = document.createElement('button');
    dialog.append(button);
    const field = document.createElement('input');
    document.body.append(dialog, field);
    fireEvent.keyDown(button, { key: 'Escape' });
    fireEvent.keyDown(field, { key: 'Escape' });
    expect(onClose).not.toHaveBeenCalled();
    dialog.remove();
    field.remove();
  });
});

it('explains automated conflict and unrest coding without labelling it verified', () => {
  render(
    <EventInspector
      event={liveEvent({ source_id: 'gdelt_events', category: 'conflict', subtype: 'protest' })}
      onClose={vi.fn()}
    />,
  );
  expect(screen.getByText('Conflict & unrest')).toBeInTheDocument();
  expect(
    screen.getByText(/Automated news coding, not an independently verified incident/),
  ).toBeInTheDocument();
  expect(screen.getByText(/not a conflict boundary/)).toBeInTheDocument();
});

describe('LayerPanel', () => {
  it('lists additional topics with counts and reports the live connection and budget', async () => {
    const onToggle = vi.fn();
    const onWindow = vi.fn();
    render(
      <LayerPanel
        counts={{ disaster: 3 }}
        hidden={['cyber']}
        stats={storeStats}
        status="live"
        error={null}
        windowHours={null}
        onWindow={onWindow}
        onToggle={onToggle}
      />,
    );
    const switches = screen.getAllByRole('switch');
    expect(switches).toHaveLength(5);
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
        windowHours={24}
        onWindow={vi.fn()}
        onToggle={vi.fn()}
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
    expect(within(drawer).getByText('0.50 / 1')).toBeInTheDocument();
    expect(within(drawer).getByText('Depth 10 km.')).toBeInTheDocument();
    expect(within(drawer).getByText('depth_km')).not.toBeVisible();
    await userEvent.click(within(drawer).getByText('Source fields'));
    expect(within(drawer).getByText('depth_km')).toBeVisible();
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
    expect(screen.queryByRole('link', { name: 'Open source' })).not.toBeInTheDocument();
    expect(screen.queryByText('Position')).not.toBeInTheDocument();
    expect(screen.queryByText('Severity index')).not.toBeInTheDocument();
    expect(isHttpUrl('http://example.org/x')).toBe(true);
    expect(isHttpUrl('ftp://example.org/x')).toBe(false);
    expect(isHttpUrl('not a url')).toBe(false);
    expect(isHttpUrl(null)).toBe(false);
    expect(sourceLabel('nasa_eonet')).toBe('nasa eonet');
  });
});

it('offers a research draft even when an event has no safe source URL', () => {
  render(
    <EventInspector
      event={liveEvent({ url: 'javascript:alert(1)', country_iso: 'GB' })}
      onClose={vi.fn()}
    />,
  );
  const link = screen.getByRole('link', { name: 'Research this' });
  const destination = new URL(link.getAttribute('href') ?? '', 'http://local.test');
  expect(destination.pathname).toBe('/research');
  expect(destination.searchParams.get('country')).toBe('GB');
  expect(destination.searchParams.get('question')).toContain('M4.2 near Somewhere');
  expect(destination.searchParams.get('question')).not.toContain('javascript:');
});
