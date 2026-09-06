import { useState } from 'react';

import { SourceRatingDetails } from '@/components/sources/SourceRatingDetails';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchSourceCatalogue } from '@/lib/api/sourceContext';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

export default function SourcesPage() {
  const { data, error, loading, reload } = useScopedResource(fetchSourceCatalogue);
  const [query, setQuery] = useState('');
  const search = query.trim().toLocaleLowerCase();
  const matches = data?.filter((source) =>
    [
      source.name,
      source.id,
      source.organisation,
      source.parent_organisation,
      source.category,
      source.language,
    ].some((value) => value?.toLocaleLowerCase().includes(search)),
  );
  return (
    <section className="h-full min-w-0 overflow-y-auto p-4 sm:p-6" aria-label="Source catalogue">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold">Source catalogue</h1>
          <p className="max-w-2xl text-sm text-muted">
            Current source identities and editorial rating context. Each saved report retains its
            own evidence and rating basis. A catalogue entry does not mean a source was queried for
            a particular report.
          </p>
        </header>
        <label className="flex flex-col gap-2 text-xs text-muted">
          Find a source, organisation, category or language
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="min-h-11 rounded-md border border-line bg-surface px-3 text-sm text-text focus-visible:outline-2 focus-visible:outline-ember"
          />
        </label>
        {loading && <LoadingNote label="Loading source catalogue" />}
        {error !== null && (
          <Alert tone="error">
            {describeError(error)}{' '}
            <Button variant="secondary" onClick={() => void reload()}>
              Retry sources
            </Button>
          </Alert>
        )}
        {data && (
          <p role="status" className="text-xs text-muted">
            {matches?.length ?? 0} of {data.length} sources
          </p>
        )}
        {data?.length === 0 && <p className="text-sm text-muted">No sources are registered.</p>}
        {data && data.length > 0 && matches?.length === 0 && (
          <p className="text-sm text-muted">No sources match your search.</p>
        )}
        <ul className="divide-y divide-line">
          {matches?.map((source) => (
            <li key={source.id} className="min-w-0 py-5 [overflow-wrap:anywhere]">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-base font-semibold">{source.name}</h2>
                <span className="font-mono text-xs text-muted">
                  Configured reliability {source.reliability}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted">
                {source.organisation}
                {source.parent_organisation ? ` · Parent: ${source.parent_organisation}` : ''}
              </p>
              <p className="mt-2 font-mono text-xs text-muted">
                {source.id} · {source.category} · {source.language}
              </p>
              <SourceRatingDetails rating={source.rating} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
