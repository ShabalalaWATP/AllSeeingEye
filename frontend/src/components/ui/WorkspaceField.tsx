import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { SelectField } from './Field';

export function WorkspaceField({
  workspaces,
  value,
  onChange,
  disabled = false,
}: {
  workspaces: Workspaces;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <SelectField
      label="Workspace"
      value={value}
      disabled={disabled}
      hint={
        workspaces.error
          ? 'Team access could not be checked. Personal work remains available.'
          : 'Personal work is private to you and administrators. Team work is visible to current team members.'
      }
      options={[
        { value: '', label: 'Personal' },
        ...(value && !workspaces.teams.some(({ team }) => team.id === value)
          ? [{ value, label: 'Team access unavailable' }]
          : []),
        ...workspaces.teams.map(({ team }) => ({ value: team.id, label: `Team: ${team.name}` })),
      ]}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
