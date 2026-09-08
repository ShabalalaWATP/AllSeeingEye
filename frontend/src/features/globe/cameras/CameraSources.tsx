import { useState } from 'react';
import type { CameraState } from './useCameras';

const GROUPS: Record<string, readonly string[]> = {
  'UK and Europe': [
    'tfl',
    'fintraffic',
    'asfinag',
    'netherlands',
    'iceland',
    'spain-dgt',
    'bulgaria',
    'serbia',
    'macedonia',
    'romania',
    'italy',
    'czechia',
    'slovakia',
    'germany',
    'france',
    'spain',
    'poland',
    'switzerland',
    'greece',
    'turkey',
    'europe-live',
  ],
  'United States': [
    'wsdot',
    'caltrans',
    'illinois',
    'oregon',
    'michigan',
    'indiana',
    'utah',
    'nevada',
    'louisiana',
    'florida',
    'georgia',
    'northcarolina',
    'arizona',
    'us-published',
  ],
  Canada: ['ottawa', 'quebec', 'ontario', 'alberta', 'montreal', 'toronto', 'drivebc'],
  'Asia and Middle East': [
    'hongkong',
    'taiwan',
    'singapore',
    'thailand',
    'japan',
    'taiwan-live',
    'middle-east',
    'asia-live',
    'eastasia',
    'seasia',
    'westasia',
  ],
  'Australia and New Zealand': ['australia', 'newzealand'],
  'Africa and Latin America': ['africa-live', 'latam-live'],
};

const SEARCH_ALIASES: Record<string, string> = {
  fintraffic: 'Finland',
  asfinag: 'Austria',
  caltrans: 'California',
  wsdot: 'Washington',
  hongkong: 'Hong Kong China',
  macedonia: 'North Macedonia',
  tfl: 'United Kingdom Britain London',
  australia: 'New South Wales NSW',
  'spain-dgt': 'Spain',
  drivebc: 'British Columbia',
};

/** Group discovery changes subscriptions only. Media still loads on selection. */
export function CameraSources({ cameras }: { cameras: CameraState }) {
  const [search, setSearch] = useState('');
  const providers = cameras.catalogue?.providers ?? [];
  const known = new Set(Object.values(GROUPS).flat());
  const groups = { ...GROUPS, Other: providers.filter((p) => !known.has(p.id)).map((p) => p.id) };
  const term = search.trim().toLocaleLowerCase();
  return (
    <div className="space-y-2" aria-label="Camera sources">
      <label className="block">
        Find a country, region or provider
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          maxLength={100}
          className="mt-2 min-h-11 w-full rounded border border-line bg-surface p-2"
        />
      </label>
      <p className="text-muted">
        {providers.length} supported sources. Enable a region below to load it.
      </p>
      <div className="max-h-72 overflow-y-auto">
        {Object.entries(groups).map(([name, ids]) => {
          const rows = providers.filter(
            (p) =>
              ids.includes(p.id) &&
              `${name} ${p.name} ${p.id} ${SEARCH_ALIASES[p.id] ?? ''}`
                .toLocaleLowerCase()
                .includes(term),
          );
          if (!rows.length) return null;
          const selected = rows.filter((p) => cameras.providers[p.id]).length;
          return (
            <details
              key={name}
              open={term || selected > 0 ? true : undefined}
              className="border-t border-line py-2"
            >
              <summary className="cursor-pointer py-2 text-cyan">
                {name}{' '}
                <span className="text-muted">
                  {selected}/{rows.length} enabled
                </span>
              </summary>
              <div className="flex gap-4">
                <button
                  type="button"
                  className="min-h-11 underline"
                  onClick={() =>
                    cameras.setProviderGroup(
                      rows.map((p) => p.id),
                      true,
                    )
                  }
                >
                  Enable {name}
                </button>
                <button
                  type="button"
                  className="min-h-11 underline"
                  onClick={() =>
                    cameras.setProviderGroup(
                      rows.map((p) => p.id),
                      false,
                    )
                  }
                >
                  Disable {name}
                </button>
              </div>
              {rows.map((provider) => (
                <div key={provider.id} className="border-t border-line py-2">
                  <button
                    type="button"
                    role="switch"
                    aria-label={provider.name}
                    aria-checked={cameras.providers[provider.id] ?? false}
                    onClick={() => cameras.toggleProvider(provider.id)}
                    className="min-h-11 w-full text-left"
                  >
                    {provider.name}{' '}
                    <span className="float-right">
                      {cameras.providers[provider.id] ? 'ON' : 'OFF'}
                    </span>
                  </button>
                  <p className="text-muted">
                    {provider.count} cameras ·{' '}
                    {provider.status === 'not_loaded' ? 'Not loaded' : provider.status}
                  </p>
                  {provider.message && <p className="text-muted">{provider.message}</p>}
                </div>
              ))}
            </details>
          );
        })}
        {providers.length > 0 &&
          !providers.some((p) =>
            `${p.id} ${p.name} ${SEARCH_ALIASES[p.id] ?? ''} ${Object.entries(groups).find(([, ids]) => ids.includes(p.id))?.[0] ?? ''}`
              .toLocaleLowerCase()
              .includes(term),
          ) && <p className="text-muted">No matching camera sources.</p>}
      </div>
    </div>
  );
}
