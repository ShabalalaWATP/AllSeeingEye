import { describe, expect, it } from 'vitest';
import { cyberActors, cyberSnapshot } from '@/test/fixtures.cyber';
import {
  KIND_SLOT,
  countryRows,
  kindSeries,
  kindShares,
  kpis,
  mentionedActors,
  natoCountryRows,
  sourceRows,
  stateRows,
  themeViews,
} from './cyberModel';

describe('cyber reading models', () => {
  it('keeps colour bound to the record kind and omits absent kinds from the stack', () => {
    const series = kindSeries(cyberSnapshot());
    expect(series.map((row) => row.key)).toEqual([
      'advisory',
      'ransomware_claim',
      'known_exploited_vulnerability',
      'outage_signal',
    ]);
    expect(series.find((row) => row.key === 'advisory')?.slot).toBe(KIND_SLOT.advisory);
    expect(series.find((row) => row.key === 'advisory')?.values).toEqual([0, 1]);
    expect(kindShares(cyberSnapshot()).map((part) => part.value)).toEqual([1, 0, 0, 1, 1, 1, 0]);
  });

  it('labels alliance members in country rows without inventing origins', () => {
    const rows = countryRows(cyberSnapshot());
    expect(rows).toEqual([
      { key: 'GB', label: 'United Kingdom', value: 1, note: 'NATO member' },
      { key: 'UA', label: 'Ukraine', value: 1, note: undefined },
    ]);
    expect(natoCountryRows(cyberSnapshot()).map((row) => row.key)).toEqual(['GB']);
  });

  it('orders sources by output and flags degraded delivery', () => {
    const rows = sourceRows(cyberSnapshot());
    // Equal output falls back to name order, so the ranking is stable between refreshes.
    expect(rows.map((row) => [row.label, row.note])).toEqual([
      ['IODA', 'degraded'],
      ['UK NCSC', undefined],
    ]);
  });

  it('builds lens views with matched items and briefing metadata', () => {
    const views = themeViews(cyberSnapshot());
    expect(views).toHaveLength(6);
    const ukraine = views.find((view) => view.theme === 'ukraine');
    expect(ukraine?.count).toBe(1);
    expect(ukraine?.items.map((item) => item.id)).toEqual(['outage-1']);
    expect(views.find((view) => view.theme === 'nato_allies')?.items).toEqual([]);
  });

  it('reads state associations and mentioned actors from the reference', () => {
    const actors = cyberActors.catalogue!.actors;
    expect(stateRows(cyberSnapshot(), actors)).toEqual([
      { key: 'Russia', label: 'Russia', value: 1, actors: ['APT29'] },
    ]);
    expect(stateRows(cyberSnapshot(), [])).toEqual([
      { key: 'Russia', label: 'Russia', value: 1, actors: ['G0016'] },
    ]);
    expect(mentionedActors(cyberSnapshot(), actors)).toEqual([
      { group_id: 'G0016', name: 'APT29', count: 1, state: 'Russia' },
    ]);
  });

  it('derives headline figures with their daily series', () => {
    const figures = kpis(cyberSnapshot());
    expect(figures.map((figure) => [figure.key, figure.value])).toEqual([
      ['total', 4],
      ['ransomware', 1],
      ['kev', 1],
      ['publications', 1],
      ['outages', 1],
      ['nation_state', 1],
    ]);
    expect(figures[0]?.series).toEqual([1, 3]);
    expect(figures[5]?.series).toEqual([0, 1]);
  });
});
