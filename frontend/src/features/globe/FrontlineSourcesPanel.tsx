const sources = [
  {
    name: 'ISW / Critical Threats',
    coverage: 'Ukraine control of terrain',
    access: 'Written permission required',
    description:
      'Published assessments and an interactive map. Incorporating its geodata into another mapping application requires written consent from ISW.',
    mapUrl: 'https://storymaps.arcgis.com/stories/36a7f6a6f5a9448496de641cf64bd375',
    accessUrl: 'https://understandingwar.org/fair-use-and-attribution-policy/',
    accessLabel: 'Read reuse policy',
  },
  {
    name: 'DeepStateMap',
    coverage: 'Ukraine control areas and frontlines',
    access: 'Approved API access required',
    description:
      'API access depends on the intended use. Permission to view the public map does not authorise this application to proxy or redistribute its geometry.',
    mapUrl: 'https://deepstatemap.live/',
    accessUrl: 'https://api.deepstatemap.live/request',
    accessLabel: 'View API access request',
  },
  {
    name: 'UN OCHA',
    coverage: 'Ukraine frontline, weekly published snapshots',
    access: 'Humanitarian use only',
    description:
      'A dated line derived from ISW / Critical Threats. Its humanitarian-only restriction does not establish permission for a general OSINT deployment.',
    mapUrl: 'https://gis.unocha.org/server/rest/services/Hosted/UKR_Front_Line/FeatureServer/0',
    accessUrl: 'https://gis.unocha.org/portal/home/item.html?id=ff87995e5ccb4c6bb77f116b22e2ff45',
    accessLabel: 'View dataset terms',
  },
  {
    name: 'Liveuamap',
    coverage: 'Multiple regions; frontline geometry coverage needs confirmation',
    access: 'Provider access and current terms required',
    description:
      'Its official API example uses a key and includes events and areas. Current terms and entitlement to territorial boundaries have not been verified.',
    mapUrl: 'https://liveuamap.com/',
    accessUrl: 'https://github.com/liveuamap/liveuamap.consolecsharp.api',
    accessLabel: 'View official API example',
  },
  {
    name: 'War Mapper',
    coverage: 'Ukraine updates and selected other conflict maps',
    access: 'Dataset access by arrangement',
    description:
      'Published maps and underlying geospatial datasets have different reuse conditions. Check each map date; some conflict series are historical.',
    mapUrl: 'https://warmapper.org/',
    accessUrl: 'https://warmapper.org/about',
    accessLabel: 'Read attribution and access details',
  },
] as const;

/** Access options are not live map layers. No provider is contacted on render. */
export function FrontlineSourcesPanel() {
  return (
    <section aria-label="Frontline data sources" className="space-y-4 p-3 text-xs">
      <div className="rounded-lg border border-line bg-white/[0.03] p-3">
        <h3 className="font-medium text-text">Frontlines &amp; control of terrain</h3>
        <p className="mt-2 leading-relaxed text-muted">
          No boundary feed is connected. The providers below publish maps or datasets, but their
          access terms must be resolved before displaying an updating layer here.
        </p>
        <p className="mt-2 leading-relaxed text-muted">
          Regional markers and incident reports are separate from frontline geometry. An empty area
          on the map does not establish that it is controlled by either side.
        </p>
      </div>
      <ul className="space-y-3">
        {sources.map((source) => (
          <li key={source.name} className="rounded-lg border border-line p-3">
            <h4 className="font-medium text-text">{source.name}</h4>
            <p className="mt-1 text-muted">{source.coverage}</p>
            <p className="mt-2 text-[11px] text-amber-200">{source.access}</p>
            <p className="mt-2 text-[11px] leading-relaxed text-muted">{source.description}</p>
            <div className="mt-2 flex flex-col items-start gap-1">
              <a
                href={source.mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-9 items-center text-cyan underline underline-offset-2"
              >
                Open {source.name} source
              </a>
              <a
                href={source.accessUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-9 items-center text-muted underline underline-offset-2"
              >
                {source.accessLabel}
              </a>
            </div>
          </li>
        ))}
      </ul>
      <p className="text-[11px] leading-relaxed text-muted">
        Sources reviewed 9 September 2026. This is an access directory, not a live-status check.
        Frontline assessments can be delayed, disputed or incomplete; any future layer must show its
        publisher and assessment date separately from the time it was downloaded.
      </p>
    </section>
  );
}
