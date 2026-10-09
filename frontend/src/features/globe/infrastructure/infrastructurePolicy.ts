/** The same asset IDs used by the API's installation licence decisions. */
export const INFRASTRUCTURE_SOURCES = {
  cable: 'map:submarine_cables',
  station: 'map:ground_stations',
  nuclear: 'map:nuclear_facilities',
  data_centre: 'map:data_centres',
  energy_site: 'map:energy_sites',
  semiconductor_site: 'map:semiconductor_sites',
  military_country: 'map:military_source_index',
} as const;
