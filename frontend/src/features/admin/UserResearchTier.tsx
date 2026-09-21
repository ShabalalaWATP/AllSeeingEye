import { Alert, LoadingNote } from '@/components/ui/Alert';
import { SelectField } from '@/components/ui/Field';
import { ApiError, asApiError, describeError } from '@/lib/api/errors';
import {
  researchTierSchema,
  setUserResearchTier,
  type ResearchUsagePage,
  type UserResearchAllowance,
} from '@/lib/api/researchUsage';
import { formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

interface Props {
  email: string;
  allowance: UserResearchAllowance | undefined;
  tiers: ResearchUsagePage['tiers'];
  loading: boolean;
  onUpdated: (value: UserResearchAllowance) => void;
  onReload: () => Promise<void>;
}

export function UserResearchTier({ email, allowance, tiers, loading, onUpdated, onReload }: Props) {
  const update = useAsyncAction(async (value: string) => {
    if (!allowance) return;
    try {
      onUpdated(
        await setUserResearchTier(allowance.user_id, {
          tier: researchTierSchema.parse(Number(value)),
          expected_revision: allowance.revision,
        }),
      );
    } catch (caught) {
      const error = asApiError(caught);
      if (error.status === 409 && error.code === 'conflict') {
        await onReload();
        throw new ApiError(
          409,
          'conflict',
          'This allowance changed in another session. Review the refreshed level before choosing again.',
        );
      }
      throw error;
    }
  });
  return (
    <div className="min-w-60 space-y-2">
      {loading && !allowance && <LoadingNote label="Loading research allowance" />}
      {!loading && !allowance && (
        <p className="text-xs text-muted">Research allowance unavailable.</p>
      )}
      {allowance && (
        <>
          <SelectField
            label={`Research allowance for ${email}`}
            labelHidden
            value={allowance.tier}
            disabled={loading || update.busy}
            options={tiers.map((tier) => ({
              value: String(tier.tier),
              label:
                tier.limit === null
                  ? `${tier.label}: Unlimited`
                  : `${tier.label}: ${tier.limit} runs per ${tier.period}`,
            }))}
            onChange={(event) => void update.run(event.target.value)}
          />
          {allowance.limit === null ? (
            <>
              <p className="text-xs text-muted">No limit on research runs</p>
              <p className="text-xs text-muted">
                {allowance.used} {allowance.used === 1 ? 'run' : 'runs'} recorded today (UTC)
              </p>
            </>
          ) : (
            <>
              <p className="text-xs text-muted">
                {allowance.remaining} remaining · {allowance.used} used
              </p>
              <p className="text-xs text-muted">Resets {formatUtc(allowance.resets_at)}</p>
            </>
          )}
        </>
      )}
      {update.error && <Alert tone="error">{describeError(update.error)}</Alert>}
    </div>
  );
}
