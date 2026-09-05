import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { zoomForBounds } from '@/lib/api/geo';
import { countries, liveEvent } from '@/test/fixtures';

import { CountryPanel } from './CountryPanel';
import { NationFilter, matchCountry } from './NationFilter';

const NOW = Date.UTC(2026, 8, 5, 3, 0, 0);

describe('matchCountry and zoomForBounds', () => {
  it('matches by name or code, and by prefix only when asked', () => {
    expect(matchCountry(countries, 'united kingdom', false)?.iso2).toBe('GB');
    expect(matchCountry(countries, ' ua ', false)?.iso2).toBe('UA');
    expect(matchCountry(countries, 'Ukr', false)).toBeNull();
    expect(matchCountry(countries, 'Ukr', true)?.iso2).toBe('UA');
    expect(matchCountry(countries, '', true)).toBeNull();
    expect(matchCountry(countries, 'Atlantis', true)).toBeNull();
  });

  it('zooms closer for small nations and stays on the globe for huge ones', () => {
    expect(zoomForBounds(countries[0]!.bounds)).toBe(4);
    expect(zoomForBounds(countries[1]!.bounds)).toBe(4);
    expect(zoomForBounds(countries[2]!.bounds)).toBe(1);
    expect(zoomForBounds([0, 0, 0.1, 0.1])).toBe(6);
  });
});

describe('NationFilter', () => {
  it('selects on a full name, a code, or Enter with a prefix, and clears', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <NationFilter countries={countries} value={null} onChange={onChange} />,
    );
    const input = screen.getByRole('combobox', { name: 'Nation filter' });
    expect(screen.queryByRole('button', { name: 'Clear nation filter' })).not.toBeInTheDocument();
    await user.type(input, 'United Kingdom');
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenLastCalledWith('GB');

    rerender(<NationFilter countries={countries} value="GB" onChange={onChange} />);
    expect(input).toHaveValue('United Kingdom');
    await user.click(screen.getByRole('button', { name: 'Clear nation filter' }));
    expect(onChange).toHaveBeenLastCalledWith(null);

    rerender(<NationFilter countries={countries} value={null} onChange={onChange} />);
    await user.clear(input);
    await user.type(input, 'ukr{Enter}');
    expect(onChange).toHaveBeenLastCalledWith('UA');
    expect(input).toHaveValue('Ukraine');

    await user.clear(input);
    await user.type(input, 'nowhere{Enter}');
    expect(onChange).toHaveBeenCalledTimes(3);
  });

  it('reports when the nation list could not be loaded', () => {
    render(<NationFilter countries={[]} value={null} onChange={vi.fn()} error="No atlas." />);
    expect(screen.getByRole('alert')).toHaveTextContent('Nations unavailable: No atlas.');
  });

  it('drops the selection when the text no longer names a nation', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<NationFilter countries={countries} value="GB" onChange={onChange} />);
    await user.type(screen.getByRole('combobox', { name: 'Nation filter' }), 'x');
    expect(onChange).toHaveBeenLastCalledWith(null);
  });
});

describe('CountryPanel', () => {
  it('summarises the nation by category and lists the latest events', async () => {
    const onSelect = vi.fn();
    const events = [
      liveEvent({ id: 'a', title: 'Quake near Kyiv', country_iso: 'UA' }),
      liveEvent({ id: 'b', title: 'Advisory', category: 'political', country_iso: 'UA' }),
    ];
    render(
      <CountryPanel
        country={countries[1]!}
        events={events}
        selectedId="b"
        now={NOW}
        onSelect={onSelect}
      />,
    );
    const panel = screen.getByRole('region', { name: 'Ukraine panel' });
    expect(within(panel).getByRole('heading', { name: 'Ukraine' })).toBeInTheDocument();
    expect(within(panel).getByText('UA · 2 live')).toBeInTheDocument();
    expect(within(panel).getByText('Disasters 1')).toBeInTheDocument();
    expect(within(panel).getByText('Political 1')).toBeInTheDocument();
    const buttons = within(panel).getAllByRole('button');
    expect(buttons).toHaveLength(2);
    expect(buttons[1]).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(buttons[0]!);
    expect(onSelect).toHaveBeenCalledWith(events[0]);
  });

  it('explains an empty nation', () => {
    render(
      <CountryPanel
        country={countries[0]!}
        events={[]}
        selectedId={null}
        now={NOW}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText('Nothing in the live tier for this nation.')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
