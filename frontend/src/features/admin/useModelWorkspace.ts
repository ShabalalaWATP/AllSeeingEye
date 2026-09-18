import { useRef, useState } from 'react';
import type { LlmProfile } from '@/lib/api/llm';
import { deleteLlmProfile, testLlmProfile } from '@/lib/api/llm';
import { ApiError } from '@/lib/api/errors';
import { saveModelWorkspace } from '@/lib/api/modelWorkspace';
import type { ModelWorkspaceInput } from '@/lib/api/modelWorkspace';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useResource } from '@/lib/hooks/useResource';
import { loadConnections } from './loadLlmWorkspace';
import type { ModelAssignmentChange } from './ModelAssignmentMatrix';
import type { ModelSetupAudience } from './ModelSetupWizard';

/** Cards and matrix derive from one server snapshot, never separate assignment lists. */
export function useModelWorkspace() {
  const resource = useResource(loadConnections);
  const request = useScopedRequest();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const inFlight = useRef(false);
  const begin = () => {
    if (inFlight.current) throw new ApiError(409, 'busy', 'Wait for the current change to finish.');
    inFlight.current = true;
    setBusy(true);
    return request();
  };
  const upsert = (profile: LlmProfile) =>
    resource.setData(
      (current) =>
        current && {
          ...current,
          profiles: {
            ...current.profiles,
            items: current.profiles.items.some((item) => item.id === profile.id)
              ? current.profiles.items.map((item) => (item.id === profile.id ? profile : item))
              : [...current.profiles.items, profile],
          },
        },
    );

  const changeFor = (
    change: ModelAssignmentChange,
    supplied?: LlmProfile,
  ): ModelWorkspaceInput['changes'][number] => {
    const data = resource.data;
    if (!data) throw new Error('Connections are still loading.');
    const binding = data.connections.items.find((item) =>
      change.scope === 'global'
        ? !item.team_id && !item.user_id
        : change.scope === 'team'
          ? item.team_id === change.targetId
          : item.user_id === change.targetId,
    );
    const policy = data.policies.find(
      (item) =>
        item.enabled &&
        item.period === 'day' &&
        item.scope === change.scope &&
        item.target_id === change.targetId,
    );
    const profile = supplied ?? data.profiles.items.find((item) => item.id === change.modelId);
    return {
      scope: change.scope,
      target_id: change.targetId,
      model:
        change.modelId === undefined
          ? null
          : {
              profile_id: change.modelId,
              expected_binding_revision: binding?.revision ?? null,
              expected_profile_revision: profile?.revision ?? null,
              tested_config_hash: profile?.tested_config_hash ?? null,
            },
      allowance:
        change.preset === undefined
          ? null
          : {
              preset: change.preset,
              expected_policy_id: policy?.id ?? null,
              expected_policy_revision: policy?.revision ?? null,
            },
    };
  };

  const save = async (changes: ModelWorkspaceInput['changes']) => {
    const signal = begin();
    setNotice(null);
    try {
      const saved = await saveModelWorkspace({ changes }, signal);
      signal.throwIfAborted();
      resource.setData(
        (current) =>
          current && {
            ...current,
            connections: { items: saved.connections },
            policies: saved.policies,
            profiles: {
              ...current.profiles,
              items: current.profiles.items.map((profile) => {
                const bound = saved.connections.some((item) => item.profile_id === profile.id);
                return { ...profile, is_bound: bound, enabled: bound || profile.enabled };
              }),
            },
          },
      );
      setNotice('Assignments and limits saved. Model cards are up to date.');
    } finally {
      inFlight.current = false;
      if (!signal.aborted) setBusy(false);
    }
  };

  const apply = async (profile: LlmProfile, audience: ModelSetupAudience) => {
    const targets = audience.scope === 'global' ? [null] : audience.targetIds;
    if (!targets.length) throw new Error('Select at least one team or user.');
    await save(
      targets.map((targetId) =>
        changeFor(
          {
            scope: audience.scope,
            targetId,
            modelId: profile.id,
          },
          profile,
        ),
      ),
    );
  };
  const remove = async (profile: LlmProfile) => {
    const signal = begin();
    try {
      await deleteLlmProfile(profile.id, signal);
      signal.throwIfAborted();
      resource.setData(
        (current) =>
          current && {
            ...current,
            profiles: {
              ...current.profiles,
              items: current.profiles.items.filter((item) => item.id !== profile.id),
            },
          },
      );
      setNotice('Saved model removed. A model slot is now available.');
    } finally {
      inFlight.current = false;
      if (!signal.aborted) setBusy(false);
    }
  };
  const retest = async (profile: LlmProfile) => {
    const signal = begin();
    upsert({
      ...profile,
      is_tested: false,
      tested_revision: null,
      tested_config_hash: null,
      tested_at: null,
    });
    try {
      const result = await testLlmProfile(profile.id, signal);
      signal.throwIfAborted();
      if (!result.ok || result.revision !== profile.revision || !result.tested_config_hash)
        throw new ApiError(
          422,
          'test_failed',
          result.error ?? 'The current configuration did not pass its test.',
        );
      upsert({
        ...profile,
        is_tested: true,
        tested_revision: result.revision,
        tested_config_hash: result.tested_config_hash,
        tested_at: result.tested_at,
      });
      setNotice(`${profile.name} passed its connection test.`);
    } finally {
      inFlight.current = false;
      if (!signal.aborted) setBusy(false);
    }
  };
  return {
    ...resource,
    busy,
    notice,
    upsert,
    apply,
    remove,
    retest,
    saveRow: (change: ModelAssignmentChange) => save([changeFor(change)]),
  };
}
