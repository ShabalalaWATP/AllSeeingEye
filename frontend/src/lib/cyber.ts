import type { LiveEvent } from '@/lib/api/eventSchemas';

export const CYBER_KIND_LABELS = {
  ransomware_claim: 'Ransomware claims',
  outage_signal: 'Connectivity signals',
  known_exploited_vulnerability: 'Known exploited vulnerabilities',
  advisory: 'Security advisories',
  threat_report: 'Threat reports',
  other: 'Other cyber reporting',
} as const;

export type CyberKind = keyof typeof CYBER_KIND_LABELS;
export type CyberKindFilter = CyberKind | 'all';

/** Classification follows explicit feed metadata, never inferred attack attribution. */
export function cyberKind(event: LiveEvent): CyberKind {
  if (event.subtype === 'ransomware') return 'ransomware_claim';
  if (event.subtype === 'outage') return 'outage_signal';
  return Object.hasOwn(CYBER_KIND_LABELS, event.subtype) ? (event.subtype as CyberKind) : 'other';
}

export function matchesCyberFilters(
  event: LiveEvent,
  kind: CyberKindFilter,
  query: string,
): boolean {
  if (event.category !== 'cyber') return true;
  if (kind !== 'all' && cyberKind(event) !== kind) return false;
  const text = `${event.title} ${event.summary ?? ''} ${event.source_id} ${event.country_iso ?? ''} ${Object.values(event.attributes).join(' ')}`;
  return text.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
}

/** Only source-attributed victim/outage countries qualify for country context. */
export function hasCyberCountryContext(event: LiveEvent): boolean {
  return (
    event.category === 'cyber' &&
    event.geo_confidence === 'country' &&
    event.country_iso !== null &&
    ['ransomware_claim', 'outage_signal'].includes(cyberKind(event))
  );
}

export const CYBER_SHIELD_PATH = 'M12 2 21 6v6c0 5-5 9-9 11-4-2-9-6-9-11V6l9-4Zm-4 10 3 3 5-6';

export const CYBER_SHIELD_MASK = `<path d="${CYBER_SHIELD_PATH}" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>`;

export const CYBER_SHIELD_ICON = `data:image/svg+xml;utf8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24">${CYBER_SHIELD_MASK}</svg>`)}`;
