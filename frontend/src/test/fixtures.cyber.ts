import type {
  CyberActors,
  CyberBriefing,
  CyberDays,
  CyberItem,
  CyberSnapshot,
} from '@/lib/api/cyber';
import { reportJob } from './reportJobFixture';

export const cyberItems: CyberItem[] = [
  {
    id: 'advisory-1',
    kind: 'advisory',
    title: 'APT29 campaign targets cloud accounts',
    summary:
      'An attributed advisory describes credential theft. Independent attribution remains a source assessment.',
    url: 'https://www.ncsc.gov.uk/report/example',
    source_id: 'cyber_ncsc_reports',
    source_name: 'UK NCSC',
    organisation: 'NCSC',
    published_at: '2026-09-12T10:00:00Z',
    observed_at: '2026-09-12T12:00:00Z',
    country_iso: null,
    grade: 'F6',
    actor_mentions: [{ group_id: 'G0016', matched_name: 'APT29' }],
    kev: null,
    themes: ['nation_state'],
  },
  {
    id: 'claim-1',
    kind: 'ransomware_claim',
    title: 'Example Manufacturing: claimed by Example Group',
    summary: null,
    url: 'https://www.ransomware.live/id/example',
    source_id: 'ransomware_live',
    source_name: 'Ransomware.live',
    organisation: 'ransomware.live',
    published_at: '2026-09-12T09:00:00Z',
    observed_at: '2026-09-12T12:00:00Z',
    country_iso: 'GB',
    grade: 'B3',
    actor_mentions: [],
    kev: null,
    themes: [],
  },
  {
    id: 'outage-1',
    kind: 'outage_signal',
    title: 'Internet connectivity signal in Ukraine',
    summary: 'A monitored signal dropped relative to its baseline.',
    url: 'https://ioda.inetintel.cc.gatech.edu/country/UA',
    source_id: 'ioda_outages',
    source_name: 'IODA',
    organisation: 'Georgia Tech',
    published_at: '2026-09-12T08:00:00Z',
    observed_at: '2026-09-12T12:00:00Z',
    country_iso: 'UA',
    grade: 'B2',
    actor_mentions: [],
    kev: null,
    themes: ['ukraine'],
  },
  {
    id: 'kev-1',
    kind: 'known_exploited_vulnerability',
    title: 'CVE-2026-12345: Example Product vulnerability',
    summary: 'Example product contains a vulnerability that has been exploited.',
    url: 'https://www.cisa.gov/known-exploited-vulnerabilities-catalog',
    source_id: 'cisa_kev',
    source_name: 'CISA KEV',
    organisation: 'CISA',
    published_at: '2026-09-11T00:00:00Z',
    observed_at: '2026-09-12T12:00:00Z',
    country_iso: null,
    grade: 'A1',
    actor_mentions: [],
    kev: {
      cve: 'CVE-2026-12345',
      vendor: 'Example Vendor',
      product: 'Example Product',
      date_added: '2026-09-11',
      due_date: '2026-10-01',
      ransomware_use: 'Unknown',
      cwes: 'CWE-20',
      required_action: 'Apply the vendor update and review exposed services.',
    },
    themes: [],
  },
];
export function cyberSnapshot(days: CyberDays = 2): CyberSnapshot {
  const as_of = '2026-09-12T12:00:00Z';
  const counts = (
    [
      { kind: 'ransomware_claim', count: 1 },
      { kind: 'outage_signal', count: 1 },
      { kind: 'known_exploited_vulnerability', count: 1 },
      { kind: 'advisory', count: 1 },
      { kind: 'threat_report', count: 0 },
      { kind: 'news_report', count: 0 },
      { kind: 'other', count: 0 },
    ] as const
  ).map((item) => ({ ...item }));
  return {
    as_of,
    window_days: days,
    period_from: new Date(Date.parse(as_of) - days * 86_400_000).toISOString(),
    period_to: as_of,
    coverage_note: 'Bounded retained reporting; incomplete publisher archives.',
    retained_count: 4,
    returned_count: 4,
    truncated: false,
    counts,
    timeline: [
      {
        day: '2026-09-11',
        total: 1,
        counts: counts.map((item) => ({
          ...item,
          count: item.kind === 'known_exploited_vulnerability' ? 1 : 0,
        })),
      },
      {
        day: '2026-09-12',
        total: 3,
        counts: counts.map((item) => ({
          ...item,
          count: ['advisory', 'outage_signal', 'ransomware_claim'].includes(item.kind) ? 1 : 0,
        })),
      },
    ],
    themes: [
      { theme: 'nation_state', count: 1, daily: [0, 1] },
      { theme: 'nato_allies', count: 0, daily: [0, 0] },
      { theme: 'uk_infrastructure', count: 0, daily: [0, 0] },
      { theme: 'ukraine', count: 1, daily: [0, 1] },
      { theme: 'gnss_interference', count: 0, daily: [0, 0] },
      { theme: 'critical_infrastructure', count: 0, daily: [0, 0] },
    ],
    state_mentions: [{ state: 'Russia', count: 1, group_ids: ['G0016'] }],
    top_countries: [
      { key: 'GB', count: 1 },
      { key: 'UA', count: 1 },
    ],
    actor_mentions: [{ group_id: 'G0016', name: 'APT29', count: 1 }],
    sources: [
      {
        source_id: 'cyber_ncsc_reports',
        name: 'UK NCSC',
        organisation: 'NCSC',
        url: 'https://www.ncsc.gov.uk/',
        status: 'healthy',
        last_success: as_of,
        last_error_at: null,
        retained_count: 1,
      },
      {
        source_id: 'ioda_outages',
        name: 'IODA',
        organisation: 'Georgia Tech',
        url: 'https://ioda.inetintel.cc.gatech.edu/',
        status: 'degraded',
        last_success: as_of,
        last_error_at: as_of,
        retained_count: 1,
      },
    ],
    items: structuredClone(cyberItems),
  };
}
export const cyberActors: CyberActors = {
  available: true,
  coverage_note: 'Historical reference, not evidence of current activity.',
  catalogue: {
    source_id: 'mitre_attack',
    version: '19.2',
    released_at: '2026-08-05T21:33:58.496Z',
    retrieved_at: '2026-09-12T12:00:00Z',
    source_url: 'https://github.com/mitre-attack/attack-stix-data',
    source_sha256: 'f'.repeat(64),
    licence_url: 'https://attack.mitre.org/resources/terms-of-use/',
    attribution: 'MITRE ATT&CK. Used with attribution.',
    limitations:
      'Associated names can overlap partly. Reference presence is not current attribution.',
    actors: [
      {
        group_id: 'G0016',
        name: 'APT29',
        associated_names: ['Midnight Blizzard', 'Cozy Bear'],
        description:
          'A publicly documented activity cluster with government attribution. This fixture is historical context.',
        url: 'https://attack.mitre.org/groups/G0016/',
        modified_at: '2026-08-01T00:00:00Z',
        technique_ids: ['T1078', 'T1566.001'],
        technique_count: 2,
        state_association: 'Russia',
      },
      {
        group_id: 'G0032',
        name: 'Lazarus Group',
        associated_names: ['HIDDEN COBRA'],
        description: 'Public reporting describes campaigns associated with this group.',
        url: 'https://attack.mitre.org/groups/G0032/',
        modified_at: '2026-08-01T00:00:00Z',
        technique_ids: [],
        technique_count: 0,
        state_association: 'North Korea',
      },
    ],
  },
};
export function cyberBriefing(days: CyberDays = 2): CyberBriefing {
  const snapshot = cyberSnapshot(days);
  return {
    job: reportJob({ status: 'paused', report_id: null }),
    window_days: days,
    period_from: snapshot.period_from,
    period_to: snapshot.period_to,
    next_refresh_at: new Date(Date.now() + 86_400_000).toISOString(),
    coverage_note: 'Collected cyber evidence only.',
  };
}
