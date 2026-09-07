import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { describeError } from '@/lib/api/errors';
import { deleteLlmProfile, fetchLlmModels, testLlmProfile } from '@/lib/api/llm';
import type { LlmProfile, LlmTestResult } from '@/lib/api/llm';
import type { User } from '@/lib/api/schemas';
import type { Team } from '@/lib/api/teams';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

import { LlmApplyConnection } from './LlmApplyConnection';

export interface LlmProfileRowProps {
  profile: LlmProfile;
  teams: readonly Team[];
  users?: readonly User[];
  disabled: boolean;
  applying: boolean;
  hasGlobal: boolean;
  legacyProtected: boolean;
  expanded?: boolean;
  onEdit: (profile: LlmProfile, models: readonly string[]) => void;
  onDeleted: (id: string) => void;
  onTested: (profile: LlmProfile) => void;
  onApply: (profile: LlmProfile, teamId: string | null, userId?: string) => void;
}

/** A saved draft can discover models and test credentials before any routing change. */
export function LlmProfileRow({
  profile,
  teams,
  users = [],
  disabled,
  applying,
  hasGlobal,
  legacyProtected,
  expanded = false,
  onEdit,
  onDeleted,
  onTested,
  onApply,
}: LlmProfileRowProps) {
  const request = useScopedRequest();
  const row = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (expanded) row.current?.querySelector('button')?.focus();
  }, [expanded]);
  const [result, setResult] = useState<LlmTestResult | null>(null);
  const [models, setModels] = useState<string[] | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const test = useAsyncAction(async () => {
    setResult(null);
    onTested({ ...profile, is_tested: false });
    const outcome = await testLlmProfile(profile.id, request());
    setResult(outcome);
    onTested({
      ...profile,
      is_tested: outcome.ok,
      tested_at: outcome.tested_at,
      tested_revision: outcome.revision,
      tested_config_hash: outcome.tested_config_hash,
    });
  });
  const discover = useAsyncAction(async () => {
    setModels((await fetchLlmModels(profile.id, request())).models);
  });
  const remove = useAsyncAction(async () => {
    await deleteLlmProfile(profile.id, request());
    onDeleted(profile.id);
  });
  const error = test.error ?? discover.error ?? remove.error;
  const busy = disabled || applying || test.busy || discover.busy || remove.busy;
  const bedrock = profile.provider === 'bedrock';
  const textProfile = !profile.roles.includes('embeddings');
  const tested =
    profile.is_tested &&
    profile.tested_revision === profile.revision &&
    profile.tested_config_hash !== null;
  return (
    <li ref={row} className="min-w-0 border-t border-line py-4">
      <details open={expanded}>
        <summary className="cursor-pointer text-sm font-medium">
          {profile.name}{' '}
          <span className="ml-2 font-normal text-muted">
            {tested ? 'Test passed' : 'Needs a test'}
          </span>
        </summary>
        <div className="mt-4 space-y-4">
          <div className="space-y-1 text-sm">
            <p className="break-all font-mono">
              {profile.model}
              {profile.reasoning_effort && (
                <span className="ml-2 text-muted">· {profile.reasoning_effort}</span>
              )}
            </p>
            <p className="break-all text-xs text-muted">{profile.base_url}</p>
            <p className="text-xs text-muted">
              {profile.api_key_hint ? `Stored key ending ${profile.api_key_hint}` : 'No stored key'}{' '}
              ·{' '}
              {profile.roles.includes('embeddings')
                ? `Embeddings ${profile.enabled ? 'enabled' : 'disabled'}`
                : profile.is_bound
                  ? 'Active text connection'
                  : 'Text connection draft'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {!profile.is_bound && !bedrock && (
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => void discover.run()}
                aria-label={`Load models for ${profile.name}`}
              >
                {discover.busy ? 'Loading models…' : 'Load account models'}
              </Button>
            )}
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => void test.run()}
              aria-label={`Test ${profile.name}`}
            >
              {test.busy ? 'Testing connection…' : 'Test connection'}
            </Button>
            {!profile.is_bound && (
              <Button
                variant="ghost"
                disabled={busy || legacyProtected}
                onClick={() => onEdit(profile, models ?? [])}
                aria-label={`Edit ${profile.name}`}
              >
                Edit draft
              </Button>
            )}
            {!profile.is_bound &&
              (!confirmingDelete ? (
                <Button
                  variant="ghost"
                  disabled={busy || legacyProtected}
                  onClick={() => setConfirmingDelete(true)}
                  aria-label={`Delete ${profile.name}`}
                >
                  Delete draft
                </Button>
              ) : (
                <Button
                  variant="danger"
                  disabled={busy}
                  onClick={() => void remove.run()}
                  aria-label={`Confirm delete ${profile.name}`}
                >
                  Confirm delete
                </Button>
              ))}
          </div>
          {legacyProtected && (
            <p className="text-xs text-muted">
              Apply a tested global replacement before editing or deleting this legacy connection.
            </p>
          )}
          {profile.is_bound && (
            <p className="text-xs text-muted">
              This connection is already in use. Reuse its saved credentials for another scope, or
              create a replacement to change its configuration.
            </p>
          )}
          <p className="text-xs text-muted">
            {bedrock
              ? 'Use a model or inference profile ID from the AWS console. '
              : !profile.is_bound && 'Loading models contacts this saved endpoint. '}
            Testing sends a short request and may use provider tokens. Compatibility is confirmed
            only by a successful test.
          </p>
          {models !== null && (
            <p role="status" className="text-sm text-muted">
              {models.length === 0
                ? 'The provider returned no model list. Enter a model ID in Edit draft.'
                : `${models.length} models returned by this account. Choose one in Edit draft.`}
            </p>
          )}
          {result !== null && (
            <p role="status" className={`text-sm ${result.ok ? 'text-text' : 'text-critical'}`}>
              {result.ok
                ? `Connection test passed in ${Math.round(result.latency_ms)} ms.`
                : `Connection test failed: ${result.error ?? 'No compatible response received.'}`}
            </p>
          )}
          {error !== null && <Alert tone="error">{describeError(error)}</Alert>}
          {tested && textProfile && (
            <LlmApplyConnection
              profile={profile}
              teams={teams}
              users={users}
              busy={busy}
              hasGlobal={hasGlobal}
              onApply={(teamId, userId) => onApply(profile, teamId, userId)}
            />
          )}
        </div>
      </details>
    </li>
  );
}
