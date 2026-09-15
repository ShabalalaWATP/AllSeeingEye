/** Preview the policies a call would be charged to, for an account, a team destination or system work. */
import { useState } from 'react';

import { AllowanceCard, ObservedTotals } from '@/components/aiUsage/AllowanceCards';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { previewAiUsage, type AiUsagePreview as Preview } from '@/lib/api/aiUsage';
import { asApiError, describeError } from '@/lib/api/errors';
import type { User } from '@/lib/api/schemas';
import type { Team } from '@/lib/api/teams';

const SYSTEM = '__system__';

export function AiUsagePreview({
  users,
  teams,
}: {
  users: readonly User[];
  teams: readonly Team[];
}) {
  const [account, setAccount] = useState('');
  const [team, setTeam] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const system = account === SYSTEM;

  async function run() {
    if (!account || busy) return;
    setBusy(true);
    setError(null);
    try {
      setPreview(
        await previewAiUsage(
          system ? { system: true } : { userId: account, ...(team ? { teamId: team } : {}) },
        ),
      );
    } catch (caught) {
      setError(describeError(asApiError(caught)));
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3 border-t border-line pt-5" aria-labelledby="ai-policy-preview">
      <div>
        <h3 id="ai-policy-preview" className="text-sm font-semibold">
          Preview effective allowance
        </h3>
        <p className="mt-1 text-xs leading-5 text-muted">
          Check which active policies would apply to an account, a team destination or shared system
          work such as feed translation.
        </p>
      </div>
      {error ? <Alert tone="error">{error}</Alert> : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <SelectField
          label="Charged to"
          value={account}
          disabled={busy}
          options={[
            { value: '', label: 'Choose an account' },
            { value: SYSTEM, label: 'System work' },
            ...users.map((user) => ({
              value: user.id,
              label: `${user.display_name} · ${user.email}`,
            })),
          ]}
          onChange={(event) => {
            setAccount(event.target.value);
            setPreview(null);
          }}
        />
        <SelectField
          label="Destination (optional)"
          value={team}
          disabled={busy || system}
          options={[
            { value: '', label: 'Personal workspace' },
            ...teams.map((item) => ({ value: item.id, label: item.name })),
          ]}
          onChange={(event) => {
            setTeam(event.target.value);
            setPreview(null);
          }}
        />
        <div className="flex items-end">
          <Button variant="secondary" busy={busy} disabled={!account} onClick={() => void run()}>
            Preview allowance
          </Button>
        </div>
      </div>
      {preview ? (
        <div className="space-y-3">
          <ObservedTotals label="Recorded usage" totals={preview.observed} />
          {preview.unknown_calls > 0 ? (
            <p className="text-sm text-amber" role="status">
              {preview.unknown_calls} provider calls have unconfirmed usage and remain charged
              pending review.
            </p>
          ) : null}
          {preview.items.length === 0 ? (
            <p className="text-sm text-muted">No active policy applies to this destination.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {preview.items.map((item) => (
                <AllowanceCard key={item.policy.id} item={item} />
              ))}
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}
