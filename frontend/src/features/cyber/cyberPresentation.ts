import type { CyberItem } from '@/lib/api/cyber';

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
  other: 'Cyber-related reporting whose precise activity type has not been established.',
};
export function filterCyberItems(
  items: readonly CyberItem[],
  query: string,
  kind: CyberItem['kind'] | 'all',
  country: string,
  actor: string,
) {
  const text = query.trim().toLocaleLowerCase();
  return items.filter(
    (item) =>
      (kind === 'all' || item.kind === kind) &&
      (!country || item.country_iso === country) &&
      (!actor || item.actor_mentions.some((mention) => mention.group_id === actor)) &&
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
