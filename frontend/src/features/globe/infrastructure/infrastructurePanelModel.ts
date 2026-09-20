import type { ControlIcon } from '../MapControlIcon';
import type { InfrastructureSelection, InfrastructureState } from './useInfrastructure';

export type InfrastructureGroup = 'technology' | 'infrastructure';
const GROUP_KINDS: Record<InfrastructureGroup, InfrastructureSelection['kind'][]> = {
  technology: ['cable', 'station', 'data_centre', 'semiconductor_site'],
  infrastructure: ['nuclear', 'energy_site', 'military_country'],
};

export function showsInfrastructureKind(
  kind: InfrastructureSelection['kind'],
  group?: InfrastructureGroup,
) {
  return group === undefined || GROUP_KINDS[group].includes(kind);
}

export type InfrastructureRecordsState = Pick<
  InfrastructureState,
  | 'data'
  | 'cablesEnabled'
  | 'stationsEnabled'
  | 'nuclearEnabled'
  | 'dataCentresEnabled'
  | 'energyEnabled'
  | 'semiconductorEnabled'
>;

export function filterInfrastructureRecords(
  state: InfrastructureRecordsState,
  query: string,
  group?: InfrastructureGroup,
) {
  const records: Exclude<InfrastructureSelection, { kind: 'military_country' }>[] = [
    ...(state.cablesEnabled
      ? (state.data?.cables ?? []).map((item) => ({ kind: 'cable' as const, item }))
      : []),
    ...(state.stationsEnabled
      ? (state.data?.ground_stations ?? []).map((item) => ({ kind: 'station' as const, item }))
      : []),
    ...(state.nuclearEnabled
      ? (state.data?.nuclear_facilities ?? []).map((item) => ({ kind: 'nuclear' as const, item }))
      : []),
    ...(state.dataCentresEnabled
      ? (state.data?.data_centres ?? []).map((item) => ({ kind: 'data_centre' as const, item }))
      : []),
    ...(state.energyEnabled
      ? (state.data?.energy_sites ?? []).map((item) => ({ kind: 'energy_site' as const, item }))
      : []),
    ...(state.semiconductorEnabled
      ? (state.data?.semiconductor_sites ?? []).map((item) => ({
          kind: 'semiconductor_site' as const,
          item,
        }))
      : []),
  ];
  return records
    .filter(({ kind }) => showsInfrastructureKind(kind, group))
    .filter(({ item }) =>
      [
        item.name,
        'operator' in item ? item.operator : '',
        'country' in item ? item.country : '',
        'category' in item ? item.category : '',
      ]
        .join(' ')
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
    );
}

export function infrastructureRecordDescription(
  value: Exclude<InfrastructureSelection, { kind: 'military_country' }>,
): string {
  switch (value.kind) {
    case 'nuclear':
      return `Nuclear power · ${value.item.country}`;
    case 'data_centre':
      return `Data centre · ${value.item.operator} · ${value.item.country ?? 'country unresolved'}`;
    case 'energy_site':
    case 'semiconductor_site':
      return `${value.item.kind.replace(/_/g, ' ')} · ${value.item.operator} · ${value.item.country ?? '??'}`;
    case 'station':
      return `${value.item.operator} · ${value.item.country}`;
    case 'cable':
      return `Cable segment · ${value.item.category}`;
  }
}

export interface InfrastructureChoice {
  label: string;
  kind: InfrastructureSelection['kind'];
  icon: ControlIcon;
  description: string;
  count: number | undefined;
  enabled: boolean;
  toggle: () => void;
}
export function infrastructureChoices(
  state: Pick<
    InfrastructureState,
    | 'data'
    | 'cablesEnabled'
    | 'stationsEnabled'
    | 'nuclearEnabled'
    | 'dataCentresEnabled'
    | 'energyEnabled'
    | 'semiconductorEnabled'
    | 'militaryEnabled'
    | 'militaryCountries'
    | 'toggleCables'
    | 'toggleStations'
    | 'toggleNuclear'
    | 'toggleDataCentres'
    | 'toggleEnergy'
    | 'toggleSemiconductor'
    | 'toggleMilitary'
  >,
  group?: InfrastructureGroup,
): InfrastructureChoice[] {
  return [
    {
      label: 'Undersea cables',
      kind: 'cable' as const,
      icon: 'route' as const,
      description: 'Approximate public route segments',
      count: state.data?.cables.length,
      enabled: state.cablesEnabled,
      toggle: state.toggleCables,
    },
    {
      label: 'Satellite ground stations',
      kind: 'station' as const,
      icon: 'space' as const,
      description: 'Public station locations',
      count: state.data?.ground_stations.length,
      enabled: state.stationsEnabled,
      toggle: state.toggleStations,
    },
    {
      label: 'Nuclear power facilities',
      kind: 'nuclear' as const,
      icon: 'infrastructure' as const,
      description: 'Historical power-plant inventory',
      count: state.data?.nuclear_facilities.length,
      enabled: state.nuclearEnabled,
      toggle: state.toggleNuclear,
    },
    {
      label: 'Data centres',
      kind: 'data_centre' as const,
      icon: 'connectivity' as const,
      description: 'Named OpenStreetMap data centres',
      count: state.data?.data_centres.length,
      enabled: state.dataCentresEnabled,
      toggle: state.toggleDataCentres,
    },
    {
      label: 'Oil and gas facilities',
      kind: 'energy_site' as const,
      icon: 'firms' as const,
      description: 'Key refineries, terminals, fields, platforms and pipelines',
      count: state.data?.energy_sites.length,
      enabled: state.energyEnabled,
      toggle: state.toggleEnergy,
    },
    {
      label: 'Semiconductor sites',
      kind: 'semiconductor_site' as const,
      icon: 'grid' as const,
      description: 'Wafer fabs, packaging plants and key suppliers',
      count: state.data?.semiconductor_sites.length,
      enabled: state.semiconductorEnabled,
      toggle: state.toggleSemiconductor,
    },
    {
      label: 'Military source index',
      kind: 'military_country' as const,
      icon: 'infrastructure' as const,
      description: 'Country-level official source guide, not base markers',
      count: state.militaryCountries.length,
      enabled: state.militaryEnabled,
      toggle: state.toggleMilitary,
    },
  ].filter((choice) => showsInfrastructureKind(choice.kind, group));
}
