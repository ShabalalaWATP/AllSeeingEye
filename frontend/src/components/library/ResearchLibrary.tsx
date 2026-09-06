import { useCallback, useState } from 'react';
import { Link } from 'react-router';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import { fetchLibrary } from '@/lib/api/researchLibrary';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { LibraryButton } from './LibraryButton';

export function ResearchLibrary({
  revision,
  onChanged,
}: {
  revision: number;
  onChanged: () => void;
}) {
  const [offset, setOffset] = useState(0);
  const [favourite, setFavourite] = useState(false);
  const [tag, setTag] = useState('');
  const [appliedTag, setAppliedTag] = useState('');
  const loader = useCallback(() => {
    // Revision is an invalidation token after a library mutation.
    // eslint-disable-next-line @typescript-eslint/no-meaningless-void-operator
    void revision;
    return fetchLibrary(offset, favourite, appliedTag);
  }, [offset, favourite, appliedTag, revision]);
  const library = useScopedResource(loader);
  return (
    <section
      aria-labelledby="research-library-title"
      className="space-y-4 rounded border border-line p-4"
    >
      <h2 id="research-library-title" className="text-lg font-semibold">
        My research library
      </h2>
      <p className="text-sm text-muted">
        Your saved reports, favourites and private notes. Team reports appear only while you retain
        access. Opening a report shows its current version and available version history.
      </p>
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setOffset(0);
          setAppliedTag(tag);
        }}
      >
        <TextField
          label="Filter by exact tag"
          maxLength={40}
          value={tag}
          onChange={(event) => setTag(event.target.value)}
        />
        <Button type="submit" variant="secondary">
          Apply tag filter
        </Button>
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={favourite}
            onChange={(event) => {
              setOffset(0);
              setFavourite(event.target.checked);
            }}
          />
          Favourites only
        </label>
      </form>
      {library.loading && <p role="status">Loading your library...</p>}
      {library.error && (
        <>
          <Alert tone="error">{describeError(library.error)}</Alert>
          <Button variant="secondary" onClick={() => void library.reload()}>
            Retry library
          </Button>
        </>
      )}
      {library.data && (
        <>
          <p className="text-xs text-muted">
            {library.data.total} visible saved reports match these filters.
          </p>
          {library.data.items.length === 0 && (
            <p className="text-sm text-muted">
              No saved reports on this page. Use “Save / organise” beside a report to add it.
            </p>
          )}
          <ul className="divide-y divide-line">
            {library.data.items.map(({ report, preference }) => (
              <li key={`${library.key}:${report.id}`} className="space-y-2 py-4">
                <Link className="font-medium hover:underline" to={`/reports/${report.id}`}>
                  {preference.favourite ? '★ ' : ''}
                  {report.title}
                </Link>
                <p className="text-xs text-muted">
                  {report.team_id ? 'Team report' : 'Personal report'} · Version{' '}
                  {report.latest_version} · {report.status.replaceAll('_', ' ')}
                </p>
                {preference.tags.length > 0 && (
                  <p className="text-xs text-muted">Tags: {preference.tags.join(', ')}</p>
                )}
                {preference.note && (
                  <p className="whitespace-pre-wrap text-sm">{preference.note}</p>
                )}
                <LibraryButton reportId={report.id} onChanged={onChanged} />
              </li>
            ))}
          </ul>
          <nav aria-label="Library pages" className="flex gap-2">
            <Button
              variant="secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - 20))}
            >
              Previous saved reports
            </Button>
            <Button
              variant="secondary"
              disabled={offset + 20 >= library.data.total || offset + 20 > 10000}
              onClick={() => setOffset(offset + 20)}
            >
              Next saved reports
            </Button>
          </nav>
        </>
      )}
    </section>
  );
}
