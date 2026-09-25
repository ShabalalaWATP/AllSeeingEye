import type { RadarAttackSnapshot } from '@/lib/api/cyber';

const LABELS = {
  layer3: 'Network layer (L3/4)',
  layer7: 'Application layer (L7)',
} as const;

function date(value: string) {
  return new Date(value).toLocaleString('en-GB', {
    timeZone: 'UTC',
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function RadarAttackResults({
  data,
  compact = false,
}: {
  data: RadarAttackSnapshot;
  compact?: boolean;
}) {
  if (data.status === 'not_configured' || data.status === 'disabled') {
    return (
      <p className="text-xs leading-5 text-muted">
        {data.status === 'disabled'
          ? 'Cloudflare Radar attack trends are disabled by the administrator.'
          : 'Cloudflare Radar needs a server-side Radar Read token.'}
      </p>
    );
  }
  if (data.status === 'unavailable') {
    return <p className="text-xs text-muted">Cloudflare Radar attack trends are unavailable.</p>;
  }
  return (
    <div className="space-y-3">
      {data.status !== 'ready' && (
        <p className="text-xs text-amber-200">
          {data.status === 'stale'
            ? 'Previously collected data. The latest Radar refresh failed.'
            : 'Only one Radar attack layer is available.'}
        </p>
      )}
      <div className={compact ? 'space-y-3' : 'grid gap-4 lg:grid-cols-2'}>
        {data.layers.map((layer) => (
          <section key={layer.layer} className="rounded-xl border border-line/70 bg-surface/60 p-4">
            <div className="flex items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold">{LABELS[layer.layer]}</h3>
              <span className="font-mono text-2xs text-muted">Top billing countries</span>
            </div>
            <p className="mt-1 text-[11px] text-muted">
              {date(layer.period_from)} to {date(layer.period_to)} UTC
            </p>
            <ol className="mt-4 space-y-2" aria-label={`${LABELS[layer.layer]} distribution`}>
              {layer.countries.slice(0, compact ? 3 : 10).map((country) => (
                <li key={country.country_iso}>
                  <div className="flex items-baseline justify-between gap-2 text-xs">
                    <span className="truncate">{country.country_name}</span>
                    <span className="font-mono tabular-nums text-cyan">
                      {country.share_percent.toFixed(1)}%
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 rounded-full bg-surface-2">
                    <div
                      className="h-1.5 rounded-full bg-cyan"
                      style={{ width: `${country.share_percent}%` }}
                    />
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-3 text-[11px] leading-5 text-muted">
              Share of Cloudflare-observed mitigated {layer.unit} across all target countries in
              this period. Target country follows the attacked zone’s billing country, when
              available.
            </p>
          </section>
        ))}
      </div>
      {!compact && (
        <p className="text-xs leading-5 text-muted">
          These are provider-wide distributions, not attack counts or a measure of risk to each
          country. They do not identify attackers, individual incidents or their physical locations.
          Cloudflare coverage is not all internet traffic.{' '}
          <a
            href={data.source_url}
            target="_blank"
            rel="noreferrer"
            className="text-cyan underline"
          >
            Cloudflare Radar
          </a>
          {' · '}CC BY-NC 4.0. {data.fetched_at && `Checked ${date(data.fetched_at)} UTC.`}
        </p>
      )}
    </div>
  );
}
