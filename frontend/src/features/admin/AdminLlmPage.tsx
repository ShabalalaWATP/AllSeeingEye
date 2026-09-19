import { useRef, useState, useSyncExternalStore } from 'react';
import { AdminPage } from '@/components/admin/AdminPage';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import type { LlmProfile } from '@/lib/api/llm';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { AiUsagePolicies } from './AiUsagePolicies';
import { LiveModelCards } from './LiveModelCards';
import { ModelAssignmentMatrix } from './ModelAssignmentMatrix';
import { ModelSetupWizard } from './ModelSetupWizard';
import { ModelTechnicalSettings } from './ModelTechnicalSettings';
import { useModelWorkspace } from './useModelWorkspace';

/** Authority changes discard modal credentials and previous administrator state. */
export default function AdminLlmPage() {
  const user = useAuthStore((state) => state.user);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return <ModelWorkspace key={`${user?.id}:${user?.role}:${user?.is_active}:${revision}`} />;
}

function ModelWorkspace() {
  const workspace = useModelWorkspace();
  const [editor, setEditor] = useState<{ initial?: LlmProfile } | null>(null);
  const [advanced, setAdvanced] = useState(false);
  const [policiesBusy, setPoliciesBusy] = useState(false);
  const [embeddingsBusy, setEmbeddingsBusy] = useState(false);
  const matrix = useRef<HTMLDivElement>(null);
  const { data, busy, loading, error } = workspace;
  const profiles = data?.profiles.items ?? [];
  const textProfiles = profiles.filter((profile) =>
    profile.roles.some((role) => role !== 'embeddings'),
  );
  const encrypted = data?.profiles.encryption_available ?? false;
  return (
    <AdminPage
      eyebrow="Research services"
      title="AI models & access"
      width="wide"
      actions={
        <Button
          variant="ghost"
          disabled={busy || loading || !!editor || advanced}
          onClick={() => void workspace.reload()}
        >
          Refresh workspace
        </Button>
      }
      description="Connect up to five models, then manage who can use them and how much."
    >
      {loading && <LoadingNote label="Loading model workspace" />}
      {error && <Alert tone="error">{describeError(error)}</Alert>}
      {data && !encrypted && (
        <Alert tone="warning" title="Credential storage unavailable">
          Server encryption must be configured before connecting a provider.
        </Alert>
      )}
      {workspace.notice && (
        <p role="status" className="text-sm text-good">
          {workspace.notice}
        </p>
      )}
      {data && (
        <>
          <LiveModelCards
            profiles={textProfiles}
            connections={data.connections.items}
            teams={data.teams}
            users={data.users}
            busy={busy || loading || !encrypted || advanced}
            onAdd={() => setEditor({})}
            onConfigure={(initial) => setEditor({ initial })}
            onManage={() => {
              matrix.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
              matrix.current?.focus();
            }}
            onRemove={workspace.remove}
            onRetest={workspace.retest}
          />
          <div
            ref={matrix}
            tabIndex={-1}
            className="scroll-mt-4 border-t border-line pt-6 outline-none"
          >
            <ModelAssignmentMatrix
              profiles={textProfiles}
              connections={data.connections.items}
              policies={data.policies}
              teams={data.teams}
              users={data.users}
              busy={busy || loading || advanced || !encrypted}
              onSave={workspace.saveRow}
            />
          </div>
          <div className="border-t border-line pt-4">
            <Button
              variant="ghost"
              disabled={busy || loading || policiesBusy || embeddingsBusy}
              onClick={() => {
                setAdvanced(!advanced);
                if (advanced) void workspace.reload();
              }}
            >
              {advanced
                ? 'Done with advanced settings'
                : 'Advanced limits and embedding connections'}
            </Button>
            {advanced && (
              <div className="mt-4 space-y-6">
                <AiUsagePolicies
                  users={data.users}
                  teams={data.teams}
                  onBusyChange={setPoliciesBusy}
                />
                <ModelTechnicalSettings
                  profiles={profiles}
                  onSaved={workspace.upsert}
                  onBusyChange={setEmbeddingsBusy}
                />
              </div>
            )}
          </div>
          {editor && (
            <ModelSetupWizard
              {...(editor.initial ? { initial: editor.initial } : {})}
              profiles={profiles}
              teams={data.teams}
              users={data.users}
              connections={data.connections.items}
              onSaved={workspace.upsert}
              onClose={() => setEditor(null)}
              onApply={workspace.apply}
            />
          )}
        </>
      )}
    </AdminPage>
  );
}
