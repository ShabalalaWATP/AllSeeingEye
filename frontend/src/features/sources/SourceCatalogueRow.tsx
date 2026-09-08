import { SourceRatingDetails } from '@/components/sources/SourceRatingDetails';
import type { CatalogueSource } from '@/lib/api/sourceContext';
import { coverageLabel, languageName } from './catalogueFilters';

export function SourceCatalogueRow({ source }: { source: CatalogueSource }) {
  return (
    <li className="min-w-0 py-5 [overflow-wrap:anywhere]">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-text">{source.name}</h3>
          <p className="mt-1 text-sm text-muted">
            {source.organisation}
            {source.parent_organisation ? ` · ${source.parent_organisation}` : ''}
          </p>
        </div>
        <span className="shrink-0 text-xs text-muted">
          {source.collection_mode === 'on_demand' ? 'On-demand research' : 'Scheduled feed'}
        </span>
      </div>
      <p className="mt-3 text-sm text-text/85" title={source.coverage_note}>
        {coverageLabel(source)}
      </p>
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
