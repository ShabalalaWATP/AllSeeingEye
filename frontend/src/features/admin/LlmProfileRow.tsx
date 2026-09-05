import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Td } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { deleteLlmProfile, testLlmProfile } from '@/lib/api/llm';
import type { LlmProfile, LlmTestResult } from '@/lib/api/llm';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

export interface LlmProfileRowProps {
  profile: LlmProfile;
  onEdit: (profile: LlmProfile) => void;
  onDeleted: (id: string) => void;
}

function describeTest(result: LlmTestResult): string {
  if (result.ok)
    return `OK, ${Math.round(result.latency_ms)} ms${result.model ? `, ${result.model}` : ''}`;
  return `Failed: ${result.error ?? 'unknown error'}`;
}

/** One profile with its connection test, edit and two-step delete. */
export function LlmProfileRow({ profile, onEdit, onDeleted }: LlmProfileRowProps) {
  const [result, setResult] = useState<LlmTestResult | null>(null);
  const [confirming, setConfirming] = useState(false);
  const test = useAsyncAction(async () => {
    setResult(await testLlmProfile(profile.id));
  });
  const remove = useAsyncAction(async () => {
    await deleteLlmProfile(profile.id);
    onDeleted(profile.id);
  });
  const error = test.error ?? remove.error;

  return (
    <tr>
      <Td>
        <div className="font-medium text-text">{profile.name}</div>
        <div className="font-mono text-xs text-muted">{profile.model}</div>
        <div className="text-xs text-muted">{profile.base_url}</div>
      </Td>
      <Td className="font-mono text-xs">
        {profile.api_key_hint === '' ? 'no key' : `…${profile.api_key_hint}`}
      </Td>
      <Td>
        <div className="flex flex-wrap gap-1">
          {profile.roles.map((role) => (
            <span
              key={role}
              className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-muted"
            >
              {role}
            </span>
          ))}
        </div>
      </Td>
      <Td>
        <span
          className={`rounded px-1.5 py-0.5 font-mono text-[11px] uppercase ${
            profile.enabled ? 'bg-emerald-400/15 text-emerald-300' : 'bg-zinc-500/15 text-muted'
          }`}
        >
          {profile.enabled ? 'enabled' : 'disabled'}
        </span>
      </Td>
      <Td>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            busy={test.busy}
            onClick={() => void test.run()}
            aria-label={`Test ${profile.name}`}
          >
            Test
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              onEdit(profile);
            }}
            aria-label={`Edit ${profile.name}`}
          >
            Edit
          </Button>
          {confirming ? (
            <Button
              variant="danger"
              busy={remove.busy}
              onClick={() => void remove.run()}
              aria-label={`Confirm delete ${profile.name}`}
            >
              Confirm delete
            </Button>
          ) : (
            <Button
              variant="ghost"
              onClick={() => {
                setConfirming(true);
              }}
              aria-label={`Delete ${profile.name}`}
            >
              Delete
            </Button>
          )}
        </div>
        {result !== null && (
          <p
            role="status"
            className={`mt-1 text-xs ${result.ok ? 'text-emerald-300' : 'text-critical'}`}
          >
            {describeTest(result)}
          </p>
        )}
        {error !== null && (
          <p role="alert" className="mt-1 text-xs text-critical">
            {describeError(error)}
          </p>
        )}
      </Td>
    </tr>
  );
}
