import { useState } from 'react';
import { TextField } from '@/components/ui/Field';
import type { ModelSetupAudience as Audience, ModelSetupProps } from './ModelSetupTypes';
import { MODEL_SETUP_MAX_TARGETS } from './ModelSetupTypes';

export function ModelSetupAudience({
  value,
  onChange,
  teams,
  users,
  connections,
}: {
  value: Audience;
  onChange: (value: Audience) => void;
} & Pick<ModelSetupProps, 'teams' | 'users' | 'connections'>) {
  const [search, setSearch] = useState('');
  const hasDefault = connections.some((connection) => !connection.team_id && !connection.user_id);
  const targets =
    value.scope === 'team'
      ? teams
          .filter((team) => team.is_active)
          .map((team) => ({ id: team.id, name: team.name, detail: 'Team workspace' }))
      : users
          .filter((user) => user.is_active)
          .map((user) => ({ id: user.id, name: user.display_name, detail: user.email }));
  const filtered = targets.filter((item) =>
    `${item.name} ${item.detail}`.toLowerCase().includes(search.toLowerCase()),
  );
  const replaced = connections.filter((connection) =>
    value.scope === 'team'
      ? value.targetIds.includes(connection.team_id ?? '')
      : value.scope === 'user' && value.targetIds.includes(connection.user_id ?? ''),
  ).length;
  return (
    <div className="space-y-5">
      <fieldset className="grid gap-2 sm:grid-cols-3">
        <legend className="sr-only">Connection audience</legend>
        {(
          [
            { scope: 'global', label: 'Global default' },
            { scope: 'team', label: 'Specific teams' },
            { scope: 'user', label: 'Specific people' },
          ] as const
        ).map((option) => (
          <label
            key={option.scope}
            className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-3 text-sm ${value.scope === option.scope ? 'border-ember bg-ember/5' : 'border-line'}`}
          >
            <input
              type="radio"
              name="audience"
              value={option.scope}
              checked={value.scope === option.scope}
              disabled={option.scope !== 'global' && !hasDefault}
              onChange={() => {
                setSearch('');
                onChange({ scope: option.scope, targetIds: [] });
              }}
            />
            {option.label}
          </label>
        ))}
      </fieldset>
      {!hasDefault && (
        <p className="text-sm text-muted">
          Set a global default before assigning models to specific teams or people.
        </p>
      )}
      {value.scope === 'global' ? (
        <p className="rounded-lg border border-amber/30 bg-amber/5 p-3 text-sm leading-6">
          This changes the default for all users and teams without their own override. Existing team
          and personal overrides keep their current model.
        </p>
      ) : (
        <>
          <TextField
            label={value.scope === 'team' ? 'Find teams' : 'Find people'}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <div className="max-h-48 overflow-y-auto rounded-lg border border-line">
            {filtered.length === 0 && (
              <p className="p-4 text-sm text-muted">
                No matching {value.scope === 'team' ? 'teams' : 'people'}.
              </p>
            )}
            {filtered.map((target) => (
              <label
                aria-label={`${target.name} ${target.detail}`}
                key={target.id}
                className="flex cursor-pointer items-center gap-3 border-b border-line/60 px-3 py-3 last:border-0 hover:bg-surface-2"
              >
                <input
                  aria-label={`${target.name} ${target.detail}`}
                  type="checkbox"
                  checked={value.targetIds.includes(target.id)}
                  disabled={
                    !hasDefault ||
                    (!value.targetIds.includes(target.id) &&
                      value.targetIds.length >= MODEL_SETUP_MAX_TARGETS)
                  }
                  onChange={(event) =>
                    onChange({
                      ...value,
                      targetIds: event.target.checked
                        ? [...value.targetIds, target.id]
                        : value.targetIds.filter((id) => id !== target.id),
                    })
                  }
                />
                <span className="min-w-0 text-sm">
                  <span className="block truncate font-medium">{target.name}</span>
                  <span className="block truncate text-xs text-muted">{target.detail}</span>
                </span>
              </label>
            ))}
          </div>
          <p role="status" className="text-xs text-muted">
            {value.targetIds.length} selected / {MODEL_SETUP_MAX_TARGETS} maximum
            {replaced > 0 ? ` · ${replaced} existing overrides will be replaced` : ''}.
          </p>
          {value.targetIds.length >= MODEL_SETUP_MAX_TARGETS && (
            <p className="text-xs text-muted">
              Selection limit reached. Deselect an item to choose another.
            </p>
          )}
          <p className="text-sm leading-6 text-muted">
            {value.scope === 'team'
              ? 'Only research in the selected team workspaces changes. Other teams and personal workspaces keep their current models.'
              : 'Only these personal workspaces change. Their team research still follows the team model or global default.'}
          </p>
        </>
      )}
    </div>
  );
}
