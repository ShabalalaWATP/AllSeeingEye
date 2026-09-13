/** Presentation vocabulary for the cyber theme lenses. Lenses are text matches, not attribution. */
import type { CyberTheme } from '@/lib/api/cyber';

export interface CyberThemeMeta {
  label: string;
  short: string;
  detail: string;
  /** Heading fragments the AI briefing uses for this lens, matched case-insensitively. */
  briefingHeadings: readonly string[];
}

export const CYBER_THEME_META: Record<CyberTheme, CyberThemeMeta> = {
  nation_state: {
    label: 'Nation-state activity',
    short: 'Nation-state',
    detail:
      'Reporting that names state-linked tradecraft, intelligence services or groups whose reference profile records a state association.',
    briefingHeadings: ['nation-state', 'nation state', 'state-sponsored', 'actor reporting'],
  },
  nato_allies: {
    label: 'NATO members and allies',
    short: 'NATO and allies',
    detail:
      'Reporting that mentions the alliance, allied defence and government bodies, or a member state together with incident language.',
    briefingHeadings: ['nato', 'allied'],
  },
  uk_infrastructure: {
    label: 'UK critical national infrastructure',
    short: 'UK infrastructure',
    detail:
      'UK context (including NCSC publications and UK-attributed records) combined with infrastructure or connectivity terms.',
    briefingHeadings: ['uk critical', 'united kingdom', 'uk infrastructure'],
  },
  ukraine: {
    label: 'Ukraine',
    short: 'Ukraine',
    detail:
      'CERT-UA publications, Ukraine-attributed records and reporting that names Ukrainian places, organisations or tracked clusters.',
    briefingHeadings: ['ukraine'],
  },
  gnss_interference: {
    label: 'GNSS interference and navigation warfare',
    short: 'GNSS interference',
    detail:
      'Reporting about GPS or other satellite navigation jamming and spoofing. The aircraft-derived interference map is shown separately.',
    briefingHeadings: ['gnss', 'navigation warfare', 'gps'],
  },
  critical_infrastructure: {
    label: 'Critical infrastructure and OT',
    short: 'Infrastructure and OT',
    detail:
      'Industrial control, energy, water, transport, health and telecommunications reporting, including ICS vendor advisories.',
    briefingHeadings: ['critical infrastructure', 'operational technology', 'ics'],
  },
};

/** ISO 3166-1 alpha-2 codes of the 32 NATO member states (2024 enlargement included). */
export const NATO_MEMBER_ISO = new Set([
  'AL',
  'BE',
  'BG',
  'CA',
  'HR',
  'CZ',
  'DK',
  'EE',
  'FI',
  'FR',
  'DE',
  'GR',
  'HU',
  'IS',
  'IT',
  'LV',
  'LT',
  'LU',
  'ME',
  'NL',
  'MK',
  'NO',
  'PL',
  'PT',
  'RO',
  'SK',
  'SI',
  'ES',
  'SE',
  'TR',
  'GB',
  'US',
]);
