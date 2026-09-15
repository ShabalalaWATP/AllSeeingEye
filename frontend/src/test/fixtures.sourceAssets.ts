import type { components } from '@/lib/api/types.gen';
import { sourceContext } from './fixtures.researchMetadata';

type Asset = components['schemas']['SourceAssetOut'];
type Source = components['schemas']['SourceSummaryOut'];

export const cameraAsset: Asset = {
  id: 'camera:tfl',
  name: 'Transport for London',
  family: 'camera_index',
  delivery: 'official_index',
  organisation: 'Transport for London',
  description: 'Public camera provider in the CCTV layer.',
  licence_note: 'Powered by TfL Open Data.',
  homepage: 'https://tfl.gov.uk/info-for/open-data-users/',
  coverage_note: 'London',
  refresh_note: 'Cached for 15 minutes after the map requests this provider.',
  state: 'on_demand',
  detail: "Loads from the publisher's index when the map asks for it.",
  requirement: null,
  as_of: null,
  records: null,
};

export const curatedCameraAsset: Asset = {
  ...cameraAsset,
  id: 'camera:uk-live',
  name: 'UK public streams',
  organisation: 'UK public streams',
  delivery: 'curated_catalogue',
  homepage: null,
  state: 'available',
  detail: 'Packaged catalogue served from the application; no upstream request.',
};

export const wsdotAsset: Asset = {
  ...cameraAsset,
  id: 'camera:wsdot',
  name: 'WSDOT',
  organisation: 'WSDOT',
  coverage_note: 'Washington State',
  state: 'key_missing',
  detail: 'Set ASE_WSDOT_ACCESS_CODE on the server to load Washington State cameras.',
  requirement: {
    kind: 'api_key',
    satisfied: false,
    origin: 'none',
    setting: 'ASE_WSDOT_ACCESS_CODE',
    note: 'Set ASE_WSDOT_ACCESS_CODE on the server to load Washington State cameras.',
    optional: false,
  },
};

export const dataCentreAsset: Asset = {
  id: 'map:data_centres',
  name: 'Data centres',
  family: 'map_layer',
  delivery: 'bundled_snapshot',
  organisation: 'OpenStreetMap contributors',
  description: 'Named data centre features on the infrastructure layer.',
  licence_note: '© OpenStreetMap contributors (ODbL).',
  homepage: 'https://www.openstreetmap.org/',
  coverage_note: 'Worldwide; incomplete and uneven between countries.',
  refresh_note: 'Refresh with ase import-data-centres.',
  state: 'available',
  detail: 'Packaged snapshot served from the application; no upstream request.',
  requirement: null,
  as_of: '2026-09-13',
  records: 3622,
};

export const deepStateAsset: Asset = {
  ...dataCentreAsset,
  id: 'ukraine:deepstate',
  name: 'DeepStateMap frontline',
  family: 'ukraine_dataset',
  delivery: 'request_service',
  organisation: 'DeepStateMap.live',
  homepage: 'https://deepstatemap.live/',
  state: 'disabled_by_environment',
  detail: 'Off until the operator records the terms this provider rests on.',
  requirement: {
    kind: 'toggle',
    satisfied: false,
    origin: 'environment',
    setting: 'ASE_UKRAINE_DEEPSTATE_ACCESS',
    note: 'Set ASE_UKRAINE_DEEPSTATE_ACCESS=granted only after DeepStateMap grants API use.',
    optional: true,
  },
  as_of: null,
  records: null,
};

export const figuresAsset: Asset = {
  ...dataCentreAsset,
  id: 'reference:public_figures',
  name: 'Public figures',
  family: 'reference_dataset',
  organisation: 'Wikidata',
  description: 'Heads of state, ministers and other office holders with portraits.',
  licence_note: 'Wikidata (CC0).',
  homepage: null,
  state: 'degraded',
  detail: 'A retry is scheduled.',
  records: 103,
};

export const blockedSource: Source = {
  ...sourceContext,
  id: 'cyber_cisa_advisories',
  name: 'US CISA cybersecurity and ICS advisories',
  category: 'cyber',
  connection: {
    ...sourceContext.connection,
    state: 'blocked_upstream',
    detail: "CISA's advisory RSS refuses this application's HTTP client.",
    health: {
      status: 'degraded',
      last_success: null,
      last_error_at: '2026-09-15T08:00:00Z',
      consecutive_failures: 0,
      items_last_poll: 0,
      next_poll_at: '2026-09-15T20:00:00Z',
      polls: 1,
      blocked_reason: "CISA's advisory RSS refuses this application's HTTP client.",
    },
  },
};

export const catalogueAssets = [
  cameraAsset,
  curatedCameraAsset,
  wsdotAsset,
  dataCentreAsset,
  deepStateAsset,
  figuresAsset,
];
