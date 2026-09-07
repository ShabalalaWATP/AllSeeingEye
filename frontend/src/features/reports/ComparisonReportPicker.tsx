import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import type { ReportSummary } from '@/lib/api/reports';
import { listComparisonReports } from '@/lib/api/annotationComparisons';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { describeError } from '@/lib/api/errors';
export function ComparisonReportPicker({
  name,
  current,
  onSelect,
}: {
  name: string;
  current: ReportSummary;
  onSelect: (report: ReportSummary) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="space-y-2">
      <p className="text-sm">
        {name}: {current.title}
      </p>
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        Choose {name.toLowerCase()} report
      </Button>
      {open && (
        <ReportChoices
          key={current.id}
          name={name}
          onSelect={(value) => {
            onSelect(value);
            setOpen(false);
          }}
        />
      )}
    </div>
  );
}
function ReportChoices({
  name,
  onSelect,
}: {
  name: string;
  onSelect: (value: ReportSummary) => void;
}) {
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const request = useScopedRequest();
  const loader = useCallback(
    () => listComparisonReports(query, offset, request()),
    [query, offset, request],
  );
  const resource = useScopedResource(loader);
  const page = resource.data;
  return (
    <div className="space-y-3 rounded border border-line p-3" aria-label={`${name} report choices`}>
      <TextField
        label={`${name}: search report titles`}
        value={draft}
        maxLength={120}
        onChange={(event) => setDraft(event.target.value)}
      />
      <Button
        variant="secondary"
        onClick={() => {
          setQuery(draft.trim());
          setOffset(0);
        }}
      >
        Search {name.toLowerCase()} reports
      </Button>
      {resource.loading && <LoadingNote label="Loading accessible report choices" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)}{' '}
          <Button variant="secondary" onClick={() => void resource.reload()}>
            Retry report choices
          </Button>
        </Alert>
      )}
      {page && (
        <>
          {page.items.length === 0 ? (
            <p className="text-sm text-muted">No accessible report titles match this search.</p>
          ) : (
            <ul className="space-y-2">
              {page.items.map((value) => (
                <li key={value.id}>
                  <Button variant="secondary" onClick={() => onSelect(value)}>
                    Use report: {value.title}
                  </Button>
                  <p className="text-xs text-muted">
                    Created {value.created_at}; {value.latest_version} saved versions
                  </p>
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs text-muted">
            {page.total} accessible matches. Results are paginated; selection remains subject to
            comparison scope checks.
          </p>
          {page.total > 20 && (
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Previous report choices
              </Button>
              <Button
                variant="secondary"
                disabled={offset + page.limit >= page.total}
                onClick={() => setOffset(offset + page.limit)}
              >
                Next report choices
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
