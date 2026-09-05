import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';

import { useReportSearch } from './useReportSearch';

export function ReportSearch() {
  const { status, query, setQuery, submittedQuery, results, search, index } = useReportSearch();
  const busy = search.busy || index.busy;
  const data = status.data;
  return (
    <section aria-label="Semantic report search" className="space-y-3 border-t border-line pt-4">
      <h2 className="text-base font-semibold">Find related reports</h2>
      <p className="text-sm text-muted">
        Search saved assessments by meaning. The configured embeddings model processes your search
        text and reports when you choose to index them.
      </p>
      {status.loading && data === null ? <LoadingNote label="Loading search availability" /> : null}
      {status.error === null ? null : (
        <Alert tone="error">
          {describeError(status.error)}{' '}
          <Button variant="ghost" onClick={() => void status.reload()}>
            Retry search availability
          </Button>
        </Alert>
      )}
      {data === null ? null : !data.available ? (
        <p className="text-sm text-muted">
          Semantic search is unavailable. An administrator can enable a model profile with the
          embeddings role under Admin, Models.
        </p>
      ) : (
        <>
          <p className="text-xs text-muted" role="status">
            {data.indexed} of {data.total} current saved reports indexed. Search covers the newest{' '}
            {data.limit.toLocaleString()} reports. Similarity scores are not confidence ratings.
          </p>
          {data.total === 0 ? (
            <p className="text-sm text-muted">
              Generate a report before building the search index.
            </p>
          ) : data.indexed < data.total ? (
            <Button
              variant="secondary"
              busy={index.busy}
              disabled={busy}
              onClick={() => void index.run()}
            >
              Index next {data.batch_size} reports
            </Button>
          ) : null}
          {index.error === null ? null : <Alert tone="error">{describeError(index.error)}</Alert>}
          <form
            aria-label="Search saved reports"
            className="flex items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              void search.run();
            }}
          >
            <div className="flex-1">
              <TextField
                label="Report search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                maxLength={500}
                required
                placeholder="For example, risks to shipping through narrow straits"
              />
            </div>
            <Button
              type="submit"
              busy={search.busy}
              disabled={busy || !query.trim() || data.indexed === 0}
            >
              Search reports
            </Button>
          </form>
          {search.error === null ? null : <Alert tone="error">{describeError(search.error)}</Alert>}
          {results === null ? null : (
            <div aria-live="polite" className="space-y-2">
              <p className="text-sm text-muted">Results for “{submittedQuery}”</p>
              {results.items.length === 0 ? (
                <p className="text-sm">
                  No indexed reports are available. Refresh the index to include new versions.
                </p>
              ) : (
                <ol aria-label="Related reports" className="divide-y divide-line">
                  {results.items.map(({ report, score }) => (
                    <li key={report.id} className="flex justify-between gap-4 py-2 text-sm">
                      <Link className="text-data hover:underline" to={`/reports/${report.id}`}>
                        {report.title}, version {report.latest_version}
                      </Link>
                      <span className="whitespace-nowrap text-xs text-muted">
                        Similarity {score.toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
