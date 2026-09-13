import type { InfrastructureSelection } from './useInfrastructure';

const KIND_LABELS: Record<InfrastructureSelection['kind'], string> = {
  cable: 'Undersea cable segment',
  station: 'Satellite ground station',
  nuclear: 'Historical nuclear power facility',
  data_centre: 'Data centre',
  energy_site: 'Oil and gas facility',
  semiconductor_site: 'Semiconductor site',
  military_country: 'Country source index',
};
const SITE_KINDS: Record<string, string> = {
  refinery: 'Refinery',
  offshore_platform: 'Offshore platform',
  oil_facility: 'Oil facility',
  oil_field: 'Oil field',
  gas_field: 'Gas field',
  oil_terminal: 'Oil terminal',
  gas_terminal: 'Gas terminal',
  lng_terminal: 'LNG terminal',
  pipeline: 'Pipeline',
  processing_plant: 'Processing plant',
  storage_hub: 'Storage hub',
  fab: 'Wafer fab',
  packaging: 'Packaging and test',
  equipment: 'Equipment maker',
  materials: 'Materials supplier',
};

export function selectionLabel(selected: InfrastructureSelection): string {
  const kind = KIND_LABELS[selected.kind];
  if (selected.kind === 'energy_site' || selected.kind === 'semiconductor_site')
    return `${kind} · ${SITE_KINDS[selected.item.kind] ?? selected.item.kind}`;
  return kind;
}

function field(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

/** Owner, purpose, description and links for any infrastructure record that carries them. */
export function InfrastructureFacts({ selected }: { selected: InfrastructureSelection }) {
  const item = selected.item as Record<string, unknown>;
  const operator = field(item.operator);
  const owner = field(item.owner);
  const country = field(item.country) ?? field(item.country_code);
  const significance = field(item.significance);
  const description = field(item.description);
  const inception = field(item.inception);
  const precision = field(item.precision);
  const detail = field(item.detail);
  const city = field(item.city);
  const role = field(item.role);
  const listed = Array.isArray(item.links)
    ? (item.links as { label: string; url: string }[]).map((link): [string, string] => [
        link.label,
        link.url,
      ])
    : [];
  const links = listed.length
    ? listed
    : [
        ['Operator website', field(item.website)],
        ['Wikipedia', field(item.wikipedia)],
      ].filter((entry): entry is [string, string] => entry[1] !== null);
  return (
    <div className="mt-3 space-y-2 text-xs text-muted">
      {(operator ?? owner ?? country) && (
        <p>
          {operator && <span className="text-text">{operator}</span>}
          {operator && owner && owner !== operator ? ' · ' : ''}
          {owner && owner !== operator && <span>owned by {owner}</span>}
          {city ? ` · ${city}` : ''}
          {country ? ` · ${country}` : ''}
          {inception ? ` · since ${inception}` : ''}
          {role ? ` · ${role.replace(/_/g, ' ')}` : ''}
        </p>
      )}
      {significance && <p className="leading-relaxed text-text">{significance}</p>}
      {detail && <p className="leading-relaxed">{detail}</p>}
      {description && <p className="leading-relaxed">{description}</p>}
      {precision === 'city' && (
        <p className="text-amber-300">
          Placed at the named city; the site itself is not geolocated in the public record.
        </p>
      )}
      {links.length > 0 && (
        <p className="flex flex-wrap gap-3">
          {links.map(([label, url]) => (
            <a
              key={url}
              href={url}
              target="_blank"
              rel="noreferrer"
              className="text-cyan underline"
            >
              {label}
            </a>
          ))}
        </p>
      )}
    </div>
  );
}
