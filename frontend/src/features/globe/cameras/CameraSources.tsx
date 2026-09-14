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
    'traffic-scotland',
    'durham',
    'uk-live',
    'estonia',
    'tallinn',
    'baltic-live',
    'russia-live',
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
    'israel-live',
    'iraq-iran-live',
    'china-live',
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
  'traffic-scotland': 'Scotland United Kingdom Britain trunk roads motorways',
  durham: 'England United Kingdom North East Durham County Council',
  'uk-live':
    'United Kingdom Britain Scotland England Wales Northern Ireland Gloucestershire Lydney',
  estonia: 'Estonia Baltic Transpordiamet Tark Tee roads',
  tallinn: 'Estonia Tallinn junctions',
  'baltic-live': 'Estonia Latvia Riga Tallinn Kuressaare',
  'russia-live': 'Russia Saint Petersburg Omsk',
  'israel-live': 'Israel Jerusalem Western Wall',
  'iraq-iran-live': 'Iraq Iran Karbala',
  'china-live': 'China Shanghai Beijing Chengdu Hong Kong',
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
          type="search"
          placeholder="Country, region or provider"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          maxLength={100}
          className="mt-2 min-h-11 w-full rounded border border-line bg-surface p-2"
        />
      </label>
      <p className="text-muted">
        {providers.length} supported sources, all on unless switched off below.
      </p>
      {!providers.length && !cameras.loading && (
        <p role="status" className="rounded border border-line p-3 text-muted">
          No source catalogue is available. Refresh the catalogue to try again.
        </p>
      )}
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
              className="border-t border-line py-3"
            >
              <summary className="cursor-pointer py-2 font-medium text-cyan">
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
                <div key={provider.id} className="border-t border-line py-3">
                  <button
                    type="button"
                    role="switch"
                    aria-label={provider.name}
                    aria-checked={cameras.providers[provider.id] ?? false}
                    onClick={() => cameras.toggleProvider(provider.id)}
                    className="flex min-h-11 w-full items-center gap-3 text-left font-medium focus-visible:outline-2 focus-visible:outline-cyan"
                  >
                    <span className="flex-1">{provider.name}</span>
                    <span
                      aria-hidden="true"
                      className={`flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 ${cameras.providers[provider.id] ? 'bg-cyan/70' : 'bg-white/15'}`}
                    >
                      <span
                        className={`h-4 w-4 rounded-full bg-white transition-transform ${cameras.providers[provider.id] ? 'translate-x-4' : ''}`}
                      />
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
