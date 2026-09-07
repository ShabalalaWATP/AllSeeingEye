import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { generateClaims } from '@/lib/api/claims';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';

const outcomes = {
  empty: 'The model returned no supported proposals. This does not confirm that nothing happened.',
  invalid: 'The model response failed validation. No proposals were saved.',
  unavailable: 'The model connection was unavailable. No proposals were saved.',
  unsupported:
    'This report needs manual claim review because its input exceeds supported limits or contains instruction-like text.',
};

export function GenerateClaims({
  reportId,
  version,
  onSaved,
}: {
  reportId: string;
  version: number;
  onSaved: () => void;
}) {
  const [notice, setNotice] = useState('');
  const request = useScopedRequest();
  const action = useAsyncAction(async () => {
    setNotice('');
    const signal = request();
    const result = await generateClaims(reportId, version, signal);
    signal.throwIfAborted();
    if (result.status === 'completed') {
      setNotice(
        `${result.items.length} proposed claims saved. Review their attribution and supporting evidence.`,
      );
      onSaved();
    } else setNotice(outcomes[result.status]);
  });
  return (
    <div className="space-y-2">
      <p className="text-sm text-muted">
        Use the assigned AI connection to extract proposed claims from this saved version. This
        sends its captured evidence and judgements to that provider and uses model tokens.
      </p>
      <Button variant="secondary" disabled={action.busy} onClick={() => void action.run()}>
        {action.busy ? 'Generating proposed claims…' : 'Generate proposed claims'}
      </Button>
      {notice && (
        <p role="status" className="text-sm text-muted">
          {notice}
        </p>
      )}
      {action.error && <Alert tone="error">{describeError(action.error)}</Alert>}
    </div>
  );
}
