import type { BarRow } from '@/components/charts/BarList';
import type { CyberItem, CyberTheme } from '@/lib/api/cyber';
import type { Tally } from '@/lib/api/modules';

const countries = new Intl.DisplayNames(['en-GB'], { type: 'region' });
export function cyberCountry(code: string | null): string {
  if (!code) return 'Location not established';
  try {
    return countries.of(code) ?? code;
  } catch {
    return code;
  }
}
export const KIND_NOTES: Record<CyberItem['kind'], string> = {
  ransomware_claim:
    'A criminal group’s claim relayed by a reporting source. Independent confirmation may be absent.',
  outage_signal:
    'A connectivity measurement, not proof of malicious activity or an ongoing outage.',
  known_exploited_vulnerability:
    'CISA has recorded exploitation in the wild. The date shown is catalogue addition, not the start of exploitation.',
  advisory:
    'Published defensive guidance. Attribution and affected scope are the issuing source’s assessment.',
  threat_report:
    'Published threat research. An actor mentioned in a report is not automatically responsible for an incident.',
  news_report:
    'Specialist press reporting of a headline only. Claims, attribution and figures are the outlet’s and remain unverified here.',
  other: 'Cyber-related reporting whose precise activity type has not been established.',
};
export function filterCyberItems(
  items: readonly CyberItem[],
  query: string,
  kind: CyberItem['kind'] | 'all',
  country: string,
  actor: string,
  theme: CyberTheme | '' = '',
) {
  const text = query.trim().toLocaleLowerCase();
  return items.filter(
    (item) =>
      (kind === 'all' || item.kind === kind) &&
      (!country || item.country_iso === country) &&
      (!actor || item.actor_mentions.some((mention) => mention.group_id === actor)) &&
      (!theme || item.themes.includes(theme)) &&
      (!text ||
        [
          item.title,
          item.summary,
          item.source_name,
          item.kev?.cve,
          item.kev?.vendor,
          item.kev?.product,
        ]
          .filter(Boolean)
          .join(' ')
          .toLocaleLowerCase()
          .includes(text)),
  );
}
export function cyberResearchLink(subject: string): string {
  const question = `Assess the reported cyber threat activity involving ${subject}. Separate verified observations, source attribution and unconfirmed claims. Explain dates, affected sectors, defensive implications and evidence gaps with citations.`;
  return `/research?${new URLSearchParams({ question })}`;
}

/** Live-board tallies as bars. Country keys read as names; a blank key is stated plainly. */
export function liveTallyRows(rows: readonly Tally[], countries: boolean, limit = 8): BarRow[] {
  return rows.slice(0, limit).map((row) => ({
    key: row.key || 'unstated',
    label: countries ? cyberCountry(row.key || null) : row.key || 'Group not stated',
    value: row.count,
  }));
}
