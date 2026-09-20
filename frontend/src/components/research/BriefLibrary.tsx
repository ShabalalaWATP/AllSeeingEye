import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { useBriefLibrary } from './useBriefLibrary';

export function BriefLibrary() {
  const { data, loading, error, reload, pageNumber, canPrevious, canNext, previous, next } =
    useBriefLibrary();
  return (
    <div className="space-y-4 rounded-xl border border-line p-5">
      <h2 className="text-xl font-semibold">My Research Briefs</h2>
      <Link className="text-sm text-ember underline" to="/research?brief=new">
        Create a new brief
      </Link>
      {loading && <LoadingNote label="Loading saved briefs" />}
      {error && (
        <Alert tone="error">
          {describeError(error)}{' '}
          <Button variant="secondary" onClick={() => void reload()}>
            Retry briefs
          </Button>
        </Alert>
      )}
      {data?.items.length === 0 && (
        <p className="text-sm text-muted">
          {pageNumber === 1 ? 'No saved briefs yet.' : 'No more briefs on this page.'}
        </p>
      )}
      <ul className="space-y-2">
        {data?.items.map((item) => (
          <li key={item.id}>
            <Link
              className="text-sm text-text underline"
              to={`/research?brief=${item.id}&revision=${item.revision}`}
            >
              {item.title} (revision {item.revision})
            </Link>
          </li>
        ))}
      </ul>
      <nav aria-label="Research Brief pages" className="flex items-center gap-3">
        <Button variant="secondary" disabled={loading || !canPrevious} onClick={previous}>
          Previous briefs
        </Button>
        <span className="text-sm text-muted" aria-live="polite">
          Page {pageNumber}
        </span>
        <Button variant="secondary" disabled={loading || !canNext} onClick={next}>
          Next briefs
        </Button>
      </nav>
    </div>
  );
}
