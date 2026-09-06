import { useCallback, useState, useSyncExternalStore } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import {
  applyLlmConnection,
  createLlmProfile,
  fetchLlmConnections,
  fetchLlmProfiles,
  resetTeamLlmConnection,
  updateLlmProfile,
} from '@/lib/api/llm';
import type { LlmProfile, LlmProfileInput } from '@/lib/api/llm';
import { listTeams } from '@/lib/api/teams';
import type { Team } from '@/lib/api/teams';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

import { LlmConnectionSummary } from './LlmConnectionSummary';
import type { ConnectionSelection } from './LlmConnectionSummary';
import { LlmProfileForm } from './LlmProfileForm';
import { LlmProfileRow } from './LlmProfileRow';
import { legacyConnections, TEXT_ROLES } from './llmPresentation';

type Editor =
  | { mode: 'closed' }
  | { mode: 'create' }
  | { mode: 'edit' | 'replace'; profile: LlmProfile; models: readonly string[] };
async function loadConnections() {
  const [profiles, connections, teams] = await Promise.all([
    fetchLlmProfiles(),
    fetchLlmConnections(),
    listTeams(),
  ]);
  return { profiles, connections, teams };
}

/** Changing account or team authority removes drafts, typed keys and prior test receipts. */
export default function AdminLlmPage() {
  const user = useAuthStore((state) => state.user);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return <ConnectionWorkspace key={`${user?.id}:${user?.role}:${user?.is_active}:${revision}`} />;
}

function ConnectionWorkspace() {
  const { data, error, loading, setData, reload } = useResource(loadConnections);
  const [editor, setEditor] = useState<Editor>({ mode: 'closed' });
  const [notice, setNotice] = useState<string | null>(null);
  const [reuseId, setReuseId] = useState<string | null>(null);
  const upsert = useCallback(
    (profile: LlmProfile) => {
      setData((current) =>
        current === null
          ? null
          : {
              ...current,
              profiles: {
                ...current.profiles,
                items: current.profiles.items.some((item) => item.id === profile.id)
                  ? current.profiles.items.map((item) => (item.id === profile.id ? profile : item))
                  : [...current.profiles.items, profile],
              },
            },
      );
    },
    [setData],
  );
  const removed = useCallback(
    (id: string) => {
      setData((current) =>
        current === null
          ? null
          : {
              ...current,
              profiles: {
                ...current.profiles,
                items: current.profiles.items.filter((item) => item.id !== id),
              },
            },
      );
    },
    [setData],
  );
  const save = useAsyncAction(async (input: LlmProfileInput) => {
    const saved =
      editor.mode === 'edit'
        ? await updateLlmProfile(editor.profile.id, input)
        : await createLlmProfile(input);
    upsert(saved);
    setEditor({ mode: 'closed' });
    setNotice(`${saved.name} saved. Open the draft to load models or test the connection.`);
  });
  const apply = useAsyncAction(async (profile: LlmProfile, teamId: string | null) => {
    if (data === null || !profile.is_tested || profile.tested_config_hash === null) return;
    const existing = data.connections.items.find((item) => item.team_id === teamId);
    await applyLlmConnection({
      team_id: teamId,
      profile_id: profile.id,
      expected_profile_revision: profile.revision,
      tested_config_hash: profile.tested_config_hash,
      expected_binding_revision: existing?.revision ?? null,
    });
    await reload();
    setReuseId(null);
    setNotice(
      `${teamId === null ? 'Global connection' : (data.teams.find((team) => team.id === teamId)?.name ?? 'Team connection')} switched to ${profile.model}.`,
    );
  });
  const openEditor = (value: Editor) => {
    save.clearError();
    apply.clearError();
    setNotice(null);
    setEditor(value);
    setReuseId(null);
  };
  const reset = useAsyncAction(async (team: Team) => {
    const binding = data?.connections.items.find((item) => item.team_id === team.id);
    if (binding === undefined) return;
    await resetTeamLlmConnection(team.id, binding.revision);
    await reload();
    setNotice(`${team.name} now uses the global connection.`);
  });
  const encryption = data?.profiles.encryption_available ?? false;
  const profiles = data?.profiles.items ?? [];
  const reused = profiles.find((profile) => profile.id === reuseId && profile.is_bound);
  const bindings = data?.connections.items ?? [];
  const globalBinding = bindings.find((item) => item.team_id === null);
  const legacySelection = bindings.length === 0 ? legacyConnections(profiles) : [];
  const legacy = legacySelection.length > 0;
  const selected = (profileId: string): ConnectionSelection[] => {
    const profile = profiles.find((item) => item.id === profileId);
    return profile === undefined ? [] : [{ profile, roles: TEXT_ROLES }];
  };
  const global = globalBinding === undefined ? legacySelection : selected(globalBinding.profile_id);
  const teamSelections = (data?.teams ?? []).flatMap((team) => {
    const binding = bindings.find((item) => item.team_id === team.id);
    return binding === undefined
      ? []
      : [
          {
            team,
            connections: selected(binding.profile_id).map((selection) => ({
              ...selection,
              roles: selection.roles.filter((role) => role !== 'translation'),
            })),
          },
        ];
  });
  const drafts = profiles.filter(
    (profile) =>
      !profile.is_bound &&
      !legacySelection.some((selection) => selection.profile.id === profile.id),
  );
  return (
    <section className="h-full overflow-y-auto p-4 sm:p-6">
      <div className="mx-auto w-full max-w-4xl space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold">AI connections</h1>
            <p className="mt-1 text-sm text-muted">
              Choose the models used for research and reports.
            </p>
          </div>
          {editor.mode === 'closed' && (
            <Button
              onClick={() => openEditor({ mode: 'create' })}
              disabled={!encryption || loading}
            >
              Configure connection
            </Button>
          )}
        </div>
        {loading && <LoadingNote label="Loading AI connections" />}
        {error !== null && (
          <Alert tone="error">
            {describeError(error)}{' '}
            <Button variant="ghost" onClick={() => void reload()}>
              Retry
            </Button>
          </Alert>
        )}
        {data !== null && !encryption && (
          <Alert tone="warning" title="Keys cannot be stored">
            Configure server encryption before saving or testing connections. Set ASE_ENCRYPTION_KEY
            and restart the server.
          </Alert>
        )}
        {notice !== null && (
          <p role="status" className="text-sm">
            {notice}
          </p>
        )}
        {(apply.error ?? reset.error) !== null && (
          <Alert tone="error">
            {describeError(apply.error ?? reset.error)} Refresh the connections before trying the
            switch again.
          </Alert>
        )}
        {data !== null && (
          <LlmConnectionSummary
            global={global}
            teams={teamSelections}
            legacy={legacy}
            disabled={!encryption || apply.busy || reset.busy || editor.mode !== 'closed'}
            onReset={(team) => void reset.run(team)}
            onReplace={(profile) => openEditor({ mode: 'replace', profile, models: [] })}
            onReuse={(profile) => {
              apply.clearError();
              setNotice(null);
              setReuseId(profile.id);
            }}
          />
        )}
        {data !== null && reused !== undefined && editor.mode === 'closed' && (
          <section aria-label="Reuse active connection" className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold">Use an existing connection</h2>
              <Button variant="ghost" disabled={apply.busy} onClick={() => setReuseId(null)}>
                Close connection reuse
              </Button>
            </div>
            <ul>
              <LlmProfileRow
                key={`${reused.id}:${reused.revision}`}
                profile={reused}
                teams={data.teams}
                disabled={!encryption}
                applying={apply.busy || reset.busy}
                hasGlobal={globalBinding !== undefined}
                legacyProtected={false}
                expanded
                onEdit={(target, models) =>
                  openEditor({ mode: 'replace', profile: target, models })
                }
                onDeleted={removed}
                onTested={upsert}
                onApply={(target, teamId) => void apply.run(target, teamId)}
              />
            </ul>
          </section>
        )}
        {editor.mode !== 'closed' && (
          <LlmProfileForm
            key={
              editor.mode === 'create'
                ? 'new'
                : `${editor.mode}:${editor.profile.id}:${editor.profile.revision}`
            }
            initial={editor.mode === 'create' ? undefined : editor.profile}
            replacement={editor.mode === 'replace'}
            models={editor.mode === 'create' ? [] : editor.models}
            busy={save.busy}
            error={save.error === null ? null : describeError(save.error)}
            onSubmit={(input) => void save.run(input)}
            onCancel={() => openEditor({ mode: 'closed' })}
          />
        )}
        {data !== null && editor.mode === 'closed' && (
          <section aria-label="Saved connection drafts" className="space-y-3">
            <div>
              <h2 className="text-base font-semibold">Saved drafts and embeddings</h2>
              <p className="mt-1 text-sm text-muted">
                Text drafts do not change the active connection. Test and apply a draft when it is
                ready.
              </p>
            </div>
            {drafts.length === 0 ? (
              <p className="text-sm text-muted">No saved drafts.</p>
            ) : (
              <ul>
                {drafts.map((profile) => (
                  <LlmProfileRow
                    key={`${profile.id}:${profile.revision}`}
                    profile={profile}
                    teams={data.teams}
                    disabled={!encryption}
                    applying={apply.busy || reset.busy}
                    hasGlobal={globalBinding !== undefined}
                    legacyProtected={
                      globalBinding === undefined &&
                      profile.enabled &&
                      profile.roles.some((role) => TEXT_ROLES.includes(role))
                    }
                    onEdit={(target, models) =>
                      openEditor({ mode: 'edit', profile: target, models })
                    }
                    onDeleted={removed}
                    onTested={upsert}
                    onApply={(target, teamId) => void apply.run(target, teamId)}
                  />
                ))}
              </ul>
            )}
          </section>
        )}
      </div>
    </section>
  );
}
