import { SourceRatingDetails } from '@/components/sources/SourceRatingDetails';
import type { CatalogueSource } from '@/lib/api/sourceContext';
import { formatUtc } from '@/lib/format';
import { ConnectionBadge } from './ConnectionBadge';
import { coverageLabel, languageName } from './catalogueFilters';

export function SourceCatalogueRow({ source }: { source: CatalogueSource }) {
  const { connection } = source;
  const requirement = connection.requirement;
  const health = connection.health;
  return (
    <li className="min-w-0 py-5 [overflow-wrap:anywhere]">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-text">{source.name}</h3>
          <p className="mt-1 text-sm text-muted">
            {source.organisation}
            {source.parent_organisation ? ` · ${source.parent_organisation}` : ''}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2 text-xs text-muted">
          <ConnectionBadge state={connection.state} optional={requirement?.optional ?? false} />
          <span>
            {source.collection_mode === 'on_demand' ? 'On-demand research' : 'Scheduled feed'}
          </span>
        </div>
      </div>
      <p className="mt-3 text-sm text-text/85" title={source.coverage_note}>
        {coverageLabel(source)}
      </p>
      <p className="mt-2 text-xs leading-5 text-muted">
        {connection.detail !== requirement?.note && connection.detail}
        {health?.last_success && ` Last successful collection ${formatUtc(health.last_success)}.`}
        {health && !health.last_success && health.last_error_at
          ? ` Last attempt failed ${formatUtc(health.last_error_at)}.`
          : ''}
        {health && health.consecutive_failures > 0
          ? ` ${health.consecutive_failures} consecutive failures.`
          : ''}
      </p>
      {requirement && (
        <p
          className={`mt-2 text-xs leading-5 ${requirement.satisfied === false && !requirement.optional ? 'text-amber' : 'text-muted'}`}
        >
          {requirement.note}
          {requirement.setting && (
            <span className="ml-2 font-mono text-[10px] text-muted">{requirement.setting}</span>
          )}
        </p>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span>{languageName(source.language)}</span>
        <span>{source.kind === 'websocket' ? 'WebSocket' : source.kind.toUpperCase()}</span>
        <span>{source.requires_key ? 'API key required' : 'No API key required'}</span>
      </div>
      <SourceRatingDetails rating={source.rating} />
      <details className="text-xs text-muted">
        <summary className="w-fit cursor-pointer py-2 focus-visible:outline-2 focus-visible:outline-ember">
          Coverage and source details
        </summary>
        <p className="py-2 leading-relaxed">{source.coverage_note}</p>
        <p className="font-mono">
          {source.id} · Configured reliability {source.reliability}
        </p>
      </details>
    </li>
  );
}
