import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { cyberKind, hasCyberCountryContext, matchesCyberFilters } from './cyber';

it.each([
  ['ransomware', 'ransomware_claim'],
  ['outage', 'outage_signal'],
  ['known_exploited_vulnerability', 'known_exploited_vulnerability'],
  ['advisory', 'advisory'],
  ['threat_report', 'threat_report'],
  ['ransomware_claim', 'ransomware_claim'],
  ['outage_signal', 'outage_signal'],
  ['unclassified', 'other'],
])('classifies explicit %s metadata as %s', (subtype, kind) => {
  expect(cyberKind(liveEvent({ category: 'cyber', subtype }))).toBe(kind);
});

it('does not invent classification from keywords and preserves non-cyber categories', () => {
  const event = liveEvent({
    category: 'cyber',
    subtype: 'news',
    title: 'Ransomware outage at a bank',
  });
  expect(cyberKind(event)).toBe('other');
  expect(matchesCyberFilters(event, 'outage_signal', '')).toBe(false);
  expect(matchesCyberFilters({ ...event, category: 'news' }, 'outage_signal', 'absent')).toBe(true);
  expect(matchesCyberFilters({ ...event, subtype: 'advisory' }, 'advisory', ' BANK ')).toBe(true);
  expect(matchesCyberFilters(event, 'all', 'unmatched')).toBe(false);
});

it('permits only source-attributed country-level claim or outage context', () => {
  const event = liveEvent({
    category: 'cyber',
    subtype: 'ransomware',
    country_iso: 'GB',
    geo_confidence: 'country',
    point: null,
  });
  expect(hasCyberCountryContext(event)).toBe(true);
  expect(hasCyberCountryContext({ ...event, subtype: 'outage' })).toBe(true);
  for (const change of [
    { subtype: 'advisory' },
    { subtype: 'threat_report' },
    { country_iso: null },
    { geo_confidence: 'none' as const },
    { category: 'news' as const },
  ]) {
    expect(hasCyberCountryContext({ ...event, ...change })).toBe(false);
  }
});
