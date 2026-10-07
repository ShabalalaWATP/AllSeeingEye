/**
 * The Sources chapter: topics and collection modes as the source catalogue groups
 * them (features/sources and lib/categories). Counts were taken from the backend
 * catalogue for this release (scheduled connectors plus on-demand research specs,
 * before installation keys); a deployment's own Sources page shows its real state.
 * Named providers are public bodies and services whose terms allow this use; sources
 * with non-commercial terms are deliberately not named here.
 */
import { CATEGORY_STYLES } from '@/lib/categories';

export interface SourceTopic {
  id: keyof typeof CATEGORY_STYLES;
  label: string;
  colour: string;
  scheduled: number;
  onDemand: number;
  examples: readonly string[];
}

function topic(
  id: SourceTopic['id'],
  scheduled: number,
  onDemand: number,
  examples: readonly string[],
): SourceTopic {
  const style = CATEGORY_STYLES[id];
  return { id, label: style.label, colour: style.css, scheduled, onDemand, examples };
}

export const SOURCE_TOPICS: readonly SourceTopic[] = [
  topic('disaster', 13, 2, [
    'USGS',
    'GDACS',
    'NASA FIRMS',
    'NOAA tsunami centres',
    'Smithsonian GVP',
  ]),
  topic('conflict', 5, 0, ['UCDP', 'GDELT events', 'Think-tank assessments']),
  topic('news', 96, 62, ['International broadcasters', 'Multilingual news research', 'GDELT']),
  topic('aviation', 6, 0, ['Volunteer ADS-B network', 'Military and PIA views']),
  topic('maritime', 3, 0, ['AIS streams', 'NGA navigation warnings']),
  topic('space', 8, 1, ['CelesTrak', 'NOAA SWPC', 'Launch Library 2', 'Sentinel-2 footprints']),
  topic('cyber', 21, 28, [
    'CISA KEV',
    'National CERT advisories',
    'Internet outage signals',
    'MITRE ATT&CK',
    'RDAP',
  ]),
  topic('social', 68, 3, ['Curated Telegram channels', 'Mastodon', 'Bluesky']),
  topic('political', 11, 12, ['FCDO', 'UK Parliament questions', 'UN', 'US State Department']),
  topic('humanitarian', 6, 7, ['WHO outbreaks', 'IFRC GO', 'OCHA', 'IOM DTM', 'IPC']),
  topic('economic', 26, 45, ['ONS', 'Bank of England', 'SEC EDGAR', 'GLEIF', 'UK sanctions list']),
];

export const SOURCE_TOTAL = SOURCE_TOPICS.reduce(
  (sum, entry) => sum + entry.scheduled + entry.onDemand,
  0,
);
export const SCHEDULED_TOTAL = SOURCE_TOPICS.reduce((sum, entry) => sum + entry.scheduled, 0);
export const ON_DEMAND_TOTAL = SOURCE_TOTAL - SCHEDULED_TOTAL;

export const COLLECTION_MODES: readonly { title: string; body: string }[] = [
  {
    title: 'Scheduled feeds',
    body: 'Public feeds and APIs polled on their own cadence into a bounded live store that is never written to the database.',
  },
  {
    title: 'On-demand research',
    body: 'Connectors that run only when a question needs them: registries, filings, advisories, multilingual news and more.',
  },
  {
    title: 'Reference data',
    body: 'Packaged datasets for context: infrastructure registers, aircraft types, public figures and country boundaries.',
  },
  {
    title: 'Your own material',
    body: 'Private documents and media (TXT, CSV, JSON, PDF, DOCX, images and video keyframes) added to a single question.',
  },
];

export const SOURCE_CAVEAT =
  'Counts describe the catalogue in this release. Some sources need keys, accounts or licence acknowledgements, and a catalogue entry is not a promise that a provider is available.';
