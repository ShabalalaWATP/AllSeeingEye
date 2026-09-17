import { useCallback, useState, useSyncExternalStore } from 'react';

import { ADMIN_CARD, AdminPage } from '@/components/admin/AdminPage';
import { StatusPill } from '@/components/admin/StatusPill';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { applyLlmConnection, resetTeamLlmConnection, resetUserLlmConnection } from '@/lib/api/llm';
import type { LlmProfile } from '@/lib/api/llm';
import type { Team } from '@/lib/api/teams';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

import { LlmPersonalConnections } from './LlmPersonalConnections';
import { AllowanceControls, LlmDraftsSection } from './LlmWorkspaceSections';
import { LlmConnectionSummary } from './LlmConnectionSummary';
import type { ConnectionSelection } from './LlmConnectionSummary';
import { LlmConnectionJourney } from './LlmConnectionJourney';
import { loadConnections } from './loadLlmWorkspace';
import { LlmProfileRow } from './LlmProfileRow';
import { legacyConnections, TEXT_ROLES } from './llmPresentation';

type Editor =
  | { mode: 'closed' }
  | { mode: 'create' }
  | {
      mode: 'edit' | 'replace';
      profile: LlmProfile;
      models: readonly string[];
      initialScope?: string;
    };

/** Changing account or team authority removes drafts, typed keys and prior test receipts. */
export default function AdminLlmPage() {
  const user = useAuthStore((state) => state.user);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return <ConnectionWorkspace key={`${user?.id}:${user?.role}:${user?.is_active}:${revision}`} />;
}

function ConnectionWorkspace() {
  const request = useScopedRequest();
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
  const apply = useAsyncAction(
    async (profile: LlmProfile, teamId: string | null, userId?: string) => {
      if (data === null || !profile.is_tested || profile.tested_config_hash === null) return;
      const existing = data.connections.items.find(
        (item) => item.team_id === teamId && (item.user_id ?? null) === (userId ?? null),
      );
      const signal = request();
      await applyLlmConnection(
        {
          team_id: teamId,
          ...(userId ? { user_id: userId } : {}),
          profile_id: profile.id,
          expected_profile_revision: profile.revision,
          tested_config_hash: profile.tested_config_hash,
          expected_binding_revision: existing?.revision ?? null,
        },
        signal,
      );
      signal.throwIfAborted();
      await reload();
      setReuseId(null);
      setEditor({ mode: 'closed' });
      setNotice(
        `${userId ? 'Personal workspace connection' : teamId === null ? 'Global connection' : (data.teams.find((team) => team.id === teamId)?.name ?? 'Team connection')} switched to ${profile.model}.`,
      );
    },
  );
  const openEditor = (value: Editor) => {
    apply.clearError();
    setNotice(null);
    setEditor(value);
    setReuseId(null);
  };
  const reset = useAsyncAction(async (team: Team) => {
    const binding = data?.connections.items.find((item) => item.team_id === team.id);
    if (binding === undefined) return;
    const signal = request();
    await resetTeamLlmConnection(team.id, binding.revision, signal);
    signal.throwIfAborted();
    await reload();
    setNotice(`${team.name} now uses the global connection.`);
  });
  const resetPersonal = useAsyncAction(async (userId: string) => {
    const binding = data?.connections.items.find((item) => item.user_id === userId);
    if (!binding) return;
    const signal = request();
    await resetUserLlmConnection(userId, binding.revision, signal);
    signal.throwIfAborted();
    await reload();
    setNotice('Personal workspace now uses the global connection.');
  });
  const encryption = data?.profiles.encryption_available ?? false;
  const profiles = data?.profiles.items ?? [];
  const reused = profiles.find((profile) => profile.id === reuseId && profile.is_bound);
  const bindings = data?.connections.items ?? [];
  const globalBinding = bindings.find((item) => item.team_id === null && !item.user_id);
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
              roles: selection.roles,
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
    <AdminPage
      eyebrow="Research services"
      title="AI connections"
      width="narrow"
      description="Keep multiple models connected. Choose a site default, then assign different connections to teams or individual users."
      meta={
        data === null ? undefined : globalBinding !== undefined ? (
          <StatusPill tone="good">Global connection active</StatusPill>
        ) : legacy ? (
          <StatusPill tone="warning">Role-based connections in use</StatusPill>
        ) : (
          <StatusPill tone="critical">No global connection</StatusPill>
        )
      }
      actions={
        editor.mode === 'closed' ? (
          <Button onClick={() => openEditor({ mode: 'create' })} disabled={!encryption || loading}>
            Add model connection
          </Button>
        ) : undefined
      }
    >
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
      {notice !== null && editor.mode === 'closed' && (
        <p role="status" className="rounded-lg border border-ember/30 bg-ember/5 px-4 py-3 text-sm">
          {notice}
        </p>
      )}
      {(apply.error ?? reset.error ?? resetPersonal.error) !== null && (
        <Alert tone="error">
          {describeError(apply.error ?? reset.error ?? resetPersonal.error)} Refresh the connections
          before trying the switch again.
        </Alert>
      )}
      {data !== null && editor.mode === 'closed' && (
        <LlmConnectionSummary
          global={global}
          teams={teamSelections}
          legacy={legacy}
          disabled={!encryption || apply.busy || reset.busy}
          onReset={(team) => void reset.run(team)}
          onReplace={(profile, teamId) =>
            openEditor({
              mode: 'replace',
              profile,
              models: [],
              ...(teamId ? { initialScope: teamId } : {}),
            })
          }
          onReuse={(profile) => {
            apply.clearError();
            setNotice(null);
            setReuseId(profile.id);
          }}
        />
      )}
      {data !== null && editor.mode === 'closed' && (
        <LlmPersonalConnections
          bindings={bindings}
          profiles={profiles}
          users={data.users}
          disabled={!encryption || apply.busy || resetPersonal.busy}
          onReset={(id) => void resetPersonal.run(id)}
          onReplace={(profile, userId) =>
            openEditor({ mode: 'replace', profile, models: [], initialScope: `user:${userId}` })
          }
        />
      )}
      {data !== null && reused !== undefined && editor.mode === 'closed' && (
        <section aria-label="Reuse active connection" className={`${ADMIN_CARD} space-y-3`}>
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
              users={data.users}
              disabled={!encryption}
              applying={apply.busy || reset.busy}
              hasGlobal={globalBinding !== undefined}
              legacyProtected={false}
              expanded
              onEdit={(target, models) => openEditor({ mode: 'replace', profile: target, models })}
              onDeleted={removed}
              onTested={upsert}
              onApply={(target, teamId, userId) => void apply.run(target, teamId, userId)}
            />
          </ul>
        </section>
      )}
      {data !== null && editor.mode !== 'closed' && (
        <LlmConnectionJourney
          key={
            editor.mode === 'create'
              ? 'new'
              : `${editor.mode}:${editor.profile.id}:${editor.profile.revision}`
          }
          {...(editor.mode === 'create' ? {} : { initial: editor.profile })}
          replacement={editor.mode === 'replace'}
          {...(editor.mode !== 'create' && editor.initialScope
            ? { initialScope: editor.initialScope }
            : {})}
          models={editor.mode === 'create' ? [] : editor.models}
          names={profiles.map((profile) => profile.name)}
          teams={data.teams}
          users={data.users}
          hasGlobal={globalBinding !== undefined}
          applying={apply.busy}
          onSaved={(profile) => {
            upsert(profile);
            if (!profile.is_tested)
              setNotice(`${profile.name} saved. The active connection has not changed.`);
          }}
          onApply={(profile, teamId, userId) => void apply.run(profile, teamId, userId)}
          onCancel={() => setEditor({ mode: 'closed' })}
        />
      )}
      {data !== null && editor.mode === 'closed' && (
        <LlmDraftsSection
          drafts={drafts}
          teams={data.teams}
          users={data.users}
          encryption={encryption}
          applying={apply.busy || reset.busy}
          hasGlobal={globalBinding !== undefined}
          onEdit={(target, models) => openEditor({ mode: 'edit', profile: target, models })}
          onDeleted={removed}
          onTested={upsert}
          onApply={(target, teamId, userId) => void apply.run(target, teamId, userId)}
        />
      )}
      {editor.mode === 'closed' ? (
        <AllowanceControls users={data?.users ?? []} teams={data?.teams ?? []} />
      ) : null}
    </AdminPage>
  );
}
