import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { listClaims } from '@/lib/api/claims';
import type { ClaimRevision } from '@/lib/api/claims';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

export function ForecastClaimPicker({
  reportId,
  version,
  onChoose,
}: {
  reportId: string;
  version: number;
  onChoose: (value: ClaimRevision | null) => void;
}) {
  const [offset, setOffset] = useState(0);
  const request = useScopedRequest();
  const load = useCallback(
    () => listClaims(reportId, version, offset, request()),
    [reportId, version, offset, request],
  );
  const resource = useScopedResource(load);
  const choices = resource.data?.items.filter((row) => row.state === 'reviewed') ?? [];
  return (
    <div className="space-y-2">
      {resource.loading && <LoadingNote label="Loading reviewed claims" />}
      {resource.error && <Alert tone="error">{describeError(resource.error)}</Alert>}
      {resource.data && (
        <>
          <SelectField
            options={[
              { value: '', label: 'Choose a reviewed claim' },
              ...choices.map((row) => ({
                value: row.id,
                label: `${row.statement} (revision ${row.number})`,
              })),
            ]}
            key={`${resource.key}:${offset}`}
            label="Exact reviewed claim revision"
            defaultValue=""
            onChange={(e) => onChoose(choices.find((row) => row.id === e.target.value) ?? null)}
          />
          {choices.length === 0 && (
            <p>No reviewed claims on this page. Review a claim in Sources &amp; methods first.</p>
          )}
          {resource.data.total > 20 && (
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={offset === 0}
                onClick={() => {
                  onChoose(null);
                  setOffset(offset - 20);
                }}
              >
                Previous claims
              </Button>
              <Button
                variant="secondary"
                disabled={offset + 20 >= resource.data.total}
                onClick={() => {
                  onChoose(null);
                  setOffset(offset + 20);
                }}
              >
                Next claims
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
