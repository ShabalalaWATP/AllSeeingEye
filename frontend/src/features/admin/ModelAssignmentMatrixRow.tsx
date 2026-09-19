import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import type { AiPolicy } from '@/lib/api/aiUsage';
import type { LlmConnection, LlmProfile } from '@/lib/api/llm';

import type { ModelAssignmentChange } from './ModelAssignmentMatrix';
import { TEXT_ROLES } from './llmPresentation';
import {
  ALLOWANCE_PRESETS,
  currentAllowancePreset,
  describeAllowanceLimits,
  describePreset,
  type DisplayAllowancePreset,
} from './modelAllowancePresets';

const selectClass =
  'w-full min-w-44 rounded-md border border-line bg-ground px-3 py-2 text-sm text-text ' +
  'transition-colors hover:border-muted/60 focus-visible:outline-ember disabled:opacity-50';
const periodLabels = { day: 'Daily', week: 'Weekly', month: 'Monthly' };

export interface AssignmentAudience {
  scope: ModelAssignmentChange['scope'];
  targetId: string | null;
  name: string;
  detail: string;
}

export function ModelAssignmentMatrixRow({
  audience,
  connection,
  profiles,
  defaultName,
  hasDefault,
  policies,
  busy,
  saving,
  onSave,
}: {
  audience: AssignmentAudience;
  connection: LlmConnection | undefined;
  profiles: readonly LlmProfile[];
  defaultName: string;
  hasDefault: boolean;
  policies: readonly AiPolicy[];
  busy: boolean;
  saving: boolean;
  onSave: (change: ModelAssignmentChange, name: string) => Promise<void>;
}) {
  const currentModel = connection?.profile_id ?? '';
  const currentPreset = currentAllowancePreset(policies);
  const [modelId, setModelId] = useState(currentModel);
  const [preset, setPreset] = useState<DisplayAllowancePreset>(currentPreset);
  const global = audience.scope === 'global';
  const available = profiles.filter(
    (profile) =>
      profile.is_tested &&
      !profile.roles.includes('embeddings') &&
      TEXT_ROLES.every((role) => profile.roles.includes(role)),
  );
  const savedModel = profiles.find((profile) => profile.id === currentModel);
  const unavailable = currentModel !== '' && !available.some((item) => item.id === currentModel);
  const modelChanged = modelId !== currentModel;
  const presetChanged = preset !== currentPreset && preset !== 'custom';
  const changed = modelChanged || presetChanged;
  const activeOtherPeriods = policies.filter((policy) => policy.enabled && policy.period !== 'day');

  function save() {
    if (busy || !changed) return;
    void onSave(
      {
        scope: audience.scope,
        targetId: audience.targetId,
        ...(modelChanged ? { modelId: modelId === '' ? null : modelId } : {}),
        ...(presetChanged ? { preset } : {}),
      },
      audience.name,
    );
  }

  return (
    <tr className={global ? 'bg-surface-2/30' : 'transition-colors hover:bg-surface-2/20'}>
      <th scope="row" className="w-[24%] px-4 py-4 text-left align-top font-normal">
        <span className="block font-medium text-text">{audience.name}</span>
        <span className="mt-1 block max-w-64 text-xs leading-5 text-muted">{audience.detail}</span>
      </th>
      <td className="w-[31%] px-4 py-4 align-top">
        <select
          aria-label={`Model for ${audience.name}`}
          className={selectClass}
          value={modelId}
          disabled={busy || (!global && !hasDefault)}
          onChange={(event) => setModelId(event.target.value)}
        >
          {global ? (
            <option value="" disabled>
              Choose a tested model
            </option>
          ) : (
            <option value="">Use default ({defaultName})</option>
          )}
          {unavailable && (
            <option value={currentModel} disabled>
              {savedModel?.name ?? 'Current model unavailable'} ·{' '}
              {savedModel?.is_tested ? 'setup required' : 'test required'}
            </option>
          )}
          {available.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.name}
            </option>
          ))}
        </select>
        {!global && !hasDefault ? (
          <p className="mt-2 text-xs text-muted">Set the global model first.</p>
        ) : null}
        {unavailable ? (
          <p className="mt-2 text-xs text-muted">
            Current assignment kept until you choose a model.
          </p>
        ) : null}
      </td>
      <td className="w-[35%] px-4 py-4 align-top">
        <select
          aria-label={`Daily allowance for ${audience.name}`}
          className={selectClass}
          value={preset}
          disabled={busy}
          onChange={(event) => setPreset(event.target.value as DisplayAllowancePreset)}
        >
          <option value="inherit">{global ? 'No daily site cap' : 'Inherit site limits'}</option>
          {ALLOWANCE_PRESETS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
          {currentPreset === 'custom' && (
            <option value="custom" disabled>
              Custom (existing)
            </option>
          )}
        </select>
        <p className="mt-2 text-xs leading-5 text-muted">{describePreset(preset, policies)}</p>
        {activeOtherPeriods.map((policy) => (
          <p key={policy.id} className="mt-1 text-xs leading-5 text-muted">
            {periodLabels[policy.period]}: {describeAllowanceLimits(policy)}
          </p>
        ))}
      </td>
      <td className="px-4 py-4 text-right align-top">
        {changed ? (
          <div className="flex flex-col items-end gap-1">
            <Button
              aria-label={`Save ${audience.name}`}
              busy={saving}
              disabled={busy}
              onClick={save}
            >
              {saving ? 'Saving…' : 'Save'}
            </Button>
            <Button
              variant="ghost"
              aria-label={`Cancel changes for ${audience.name}`}
              disabled={busy}
              onClick={() => {
                setModelId(currentModel);
                setPreset(currentPreset);
              }}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <span className="inline-block py-2 text-xs text-muted">Saved</span>
        )}
      </td>
    </tr>
  );
}
