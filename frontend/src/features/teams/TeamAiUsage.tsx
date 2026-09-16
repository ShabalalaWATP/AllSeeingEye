/** Team AI allowance: members see their own usage, Managers and administrators see member totals. */
import { useState } from 'react';

import { AllowanceCard, ObservedTotals } from '@/components/aiUsage/AllowanceCards';
import { SPEND_CAVEAT, spendOf } from '@/components/aiUsage/spend';
import { describeError } from '@/lib/api/errors';
import { getTeamAiUsage, type TeamAiUsage as Usage } from '@/lib/api/aiUsage';

export function TeamAiUsage({ teamId }: { teamId: string }) {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setUsage(await getTeamAiUsage(teamId));
    } catch (reason) {
      setError(describeError(reason));
    } finally {
      setLoading(false);
    }
  };

  return (
    <details
      className="border border-line/70 bg-surface/40 p-5"
      onToggle={(event) => {
        if (event.currentTarget.open && usage === null && !loading) void load();
      }}
    >
      <summary className="cursor-pointer text-sm font-semibold">AI allowance</summary>
      <div className="mt-4 space-y-4">
        {loading ? <p className="text-sm text-muted">Loading allowance…</p> : null}
        {error ? <p className="text-sm text-critical">{error}</p> : null}
        {usage ? (
          <>
            <ObservedTotals label="Your team usage" totals={usage.own} prices={usage.prices} />
            {usage.team ? (
              <ObservedTotals label="Whole team" totals={usage.team} prices={usage.prices} />
            ) : null}
            {usage.items.length === 0 ? (
              <p className="text-sm text-muted">
                No allowance policy is active for this workspace; usage is recorded only.
              </p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {usage.items.map((item) => (
                  <AllowanceCard key={item.policy.id} item={item} />
                ))}
              </div>
            )}
            {usage.members ? <MemberTotals members={usage.members} prices={usage.prices} /> : null}
          </>
        ) : null}
      </div>
    </details>
  );
}

function MemberTotals({
  members,
  prices,
}: {
  members: NonNullable<Usage['members']>;
  prices: Usage['prices'];
}) {
  if (members.length === 0) {
    return <p className="text-sm text-muted">No member has used AI for this team this month.</p>;
  }
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted">{SPEND_CAVEAT}</p>
      <div className="overflow-x-auto border border-line/70">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">AI usage by team member this month</caption>
          <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2">Member</th>
              <th className="px-3 py-2">Requests</th>
              <th className="px-3 py-2">Tokens</th>
              <th className="px-3 py-2">Estimated spend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {members.map((member) => (
              <tr key={member.user_id}>
                <td className="px-3 py-2">{member.display_name}</td>
                <td className="px-3 py-2">{member.observed.used_requests.toLocaleString()}</td>
                <td className="px-3 py-2">{member.observed.used_tokens.toLocaleString()}</td>
                <td className="px-3 py-2">{spendOf(member.observed, prices) ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
