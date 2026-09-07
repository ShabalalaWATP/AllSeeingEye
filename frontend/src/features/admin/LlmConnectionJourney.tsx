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
export function LlmConnectionJourney({
  initial,
  initialScope,
  replacement,
  models,
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
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const save = async (input: LlmProfileInput, test: boolean) => {
    const signal = request();
    setBusy(true);
    setError(null);
    setTested(null);
    setNotice(null);
    try {
      const saved = draft
        ? await updateLlmProfile(draft.id, input, signal)
        : await createLlmProfile(input, signal);
      signal.throwIfAborted();
      setDraft(saved);
      onSaved(saved);
      if (test) {
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
      if (!signal.aborted) setError(describeError(failure));
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  return (
    <section aria-label="Guided AI connection setup" className="space-y-5">
      <div hidden={!!tested}>
        <LlmProfileForm
          {...((draft ?? initial) ? { initial: draft ?? initial } : {})}
          replacement={replacement && !draft}
          models={models}
          busy={busy || applying}
          error={error}
          onSubmit={(input) => void save(input, false)}
          onTest={(input) => void save(input, true)}
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
        <div className="space-y-3">
          <Button variant="ghost" disabled={applying} onClick={() => setTested(null)}>
            Back to model settings
          </Button>
          <h3 className="text-sm font-semibold">3. Review scope and confirm</h3>
          <Alert tone="warning">
            This switches the AI provider receiving research prompts and selected evidence for the
            chosen audience. Confirm only after reviewing the endpoint, model and scope.
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
