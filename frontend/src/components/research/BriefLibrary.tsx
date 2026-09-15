import { useCallback } from 'react';
import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchBriefs } from '@/lib/api/researchBriefs';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

export function BriefLibrary() {
  const loader = useCallback(async () => fetchBriefs(new AbortController().signal), []);
  const { data, loading, error, reload } = useScopedResource(loader);
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
      {data?.items.length === 0 && <p className="text-sm text-muted">No saved briefs yet.</p>}
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
    </div>
  );
}
