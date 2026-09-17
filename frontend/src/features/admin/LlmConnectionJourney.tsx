import { ADMIN_CARD } from '@/components/admin/AdminPage';
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import {
  createLlmProfile,
  updateLlmProfile,
  testLlmProfile,
  type LlmProfile,
  type LlmProfileInput,
} from '@/lib/api/llm';
import type { Team } from '@/lib/api/teams';
import type { User } from '@/lib/api/schemas';
import { ApiError, describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { LlmProfileForm } from './LlmProfileForm';
import { LlmApplyConnection } from './LlmApplyConnection';
import { LlmSetupProgress } from './LlmSetupProgress';
export function LlmConnectionJourney({
  initial,
  initialScope,
  replacement,
  models,
  names,
  teams,
  users,
  hasGlobal,
  applying,
  onSaved,
  onApply,
  onCancel,
}: {
  initial?: LlmProfile;
  initialScope?: string;
  replacement: boolean;
  models: readonly string[];
  names?: readonly string[];
  teams: Team[];
  users: User[];
  hasGlobal: boolean;
  applying: boolean;
  onSaved: (profile: LlmProfile) => void;
  onApply: (profile: LlmProfile, teamId: string | null, userId?: string) => void;
  onCancel: () => void;
}) {
  const request = useScopedRequest();
  const [draft, setDraft] = useState<LlmProfile | null>(replacement ? null : (initial ?? null));
  const [tested, setTested] = useState<LlmProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState('Saving draft…');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const save = async (
    input: LlmProfileInput,
    test: boolean,
  ): Promise<boolean | 'provider-error'> => {
    const signal = request();
    setBusy(true);
    setError(null);
    setTested(null);
    setNotice(null);
    setBusyLabel('Saving draft…');
    let persisted = false;
    try {
      const saved = draft
        ? await updateLlmProfile(draft.id, input, signal)
        : await createLlmProfile(input, signal);
      signal.throwIfAborted();
      setDraft(saved);
      onSaved(saved);
      persisted = true;
      if (test) {
        setBusyLabel('Testing with provider…');
        const result = await testLlmProfile(saved.id, signal);
        signal.throwIfAborted();
        if (!result.ok || result.revision !== saved.revision || !result.tested_config_hash)
          throw new ApiError(
            422,
            'connection_test_failed',
            result.error ?? 'This configuration did not pass the compatibility test.',
          );
        const proven = {
          ...saved,
          is_tested: true,
          tested_at: result.tested_at,
          tested_revision: result.revision,
          tested_config_hash: result.tested_config_hash,
        };
        setDraft(proven);
        onSaved(proven);
        setTested(proven);
        setNotice(
          `Connection test passed in ${Math.round(result.latency_ms)} ms. Review the scope below.`,
        );
      } else {
        setNotice('Draft saved. The active connection has not changed.');
        onCancel();
      }
    } catch (failure) {
      if (!signal.aborted)
        setError(
          `${persisted ? 'Draft saved, but the connection test failed.' : 'Could not save this draft.'} ${describeError(failure)} ${persisted ? 'Check the model and reasoning setting, then test again.' : 'Your entries are still here. Check the connection name and provider details, then retry.'} The active connection has not changed.`,
        );
      if (!persisted && failure instanceof ApiError && failure.fieldError('name'))
        return 'provider-error';
    } finally {
      if (!signal.aborted) setBusy(false);
    }
    return persisted;
  };
  return (
    <section aria-label="Guided AI connection setup" className={`${ADMIN_CARD} space-y-5`}>
      <div hidden={!!tested}>
        <LlmProfileForm
          {...((draft ?? initial) ? { initial: draft ?? initial } : {})}
          replacement={replacement && !draft}
          models={models}
          {...(names ? { names } : {})}
          busy={busy || applying}
          busyLabel={busyLabel}
          error={error}
          onSubmit={(input) => save(input, false)}
          onTest={(input) => save(input, true)}
          onChange={() => {
            setTested(null);
            setNotice(null);
          }}
          onCancel={onCancel}
        />
      </div>
      {notice && (
        <p role="status" className="text-sm">
          {notice}
        </p>
      )}
      {tested && (
        <div className="space-y-5">
          <LlmSetupProgress step={3} />
          <Button variant="ghost" disabled={applying} onClick={() => setTested(null)}>
            Back to model settings
          </Button>
          <h2 className="text-lg font-semibold">Choose who uses this connection</h2>
          <Alert tone="warning" title="You are about to change the active AI connection">
            The selected provider will receive research prompts and evidence for this audience.
            Review the details before confirming.
          </Alert>
          <LlmApplyConnection
            profile={tested}
            {...(initialScope ? { initialScope } : {})}
            teams={teams}
            users={users}
            hasGlobal={hasGlobal}
            busy={applying}
            onApply={(teamId, userId) => onApply(tested, teamId, userId)}
          />
        </div>
      )}
    </section>
  );
}
