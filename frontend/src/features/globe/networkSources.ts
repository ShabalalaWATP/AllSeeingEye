export const NETWORK_SOURCES = [
  'ioda_outages',
  'ioda_outage_events',
  'cloudflare_radar_outages',
] as const;

export function isNetworkSource(sourceId: string): boolean {
  return NETWORK_SOURCES.some((source) => source === sourceId);
}
