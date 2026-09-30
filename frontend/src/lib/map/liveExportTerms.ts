/** Reviewed eligibility for the limited metadata export, never inferred from licence prose.
 * Reviewed 30 September 2026. Unlisted sources remain excluded pending review.
 */
export interface LiveExportTerms {
  attribution: string;
  terms_url: string;
  reviewed_on: string;
}

const nasa: LiveExportTerms = {
  attribution: 'NASA FIRMS, NASA LANCE, and NOAA VIIRS. Near-real-time active-fire detections.',
  terms_url: 'https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy',
  reviewed_on: '2026-09-30',
};
export const LIVE_EXPORT_TERMS: Readonly<Record<string, LiveExportTerms>> = {
  usgs_earthquakes: {
    attribution: 'Earthquake data courtesy of the U.S. Geological Survey.',
    terms_url:
      'https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs',
    reviewed_on: '2026-09-30',
  },
  firms_viirs_noaa20: nasa,
  firms_viirs_noaa21: nasa,
  firms_public_noaa20: nasa,
  firms_public_noaa21: nasa,
};
