import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { describeError } from '@/lib/api/errors';
import type { LlmProfile, LlmConnection } from '@/lib/api/llm';
import type { Team } from '@/lib/api/teams';
import type { User } from '@/lib/api/schemas';

export const MAX_MODEL_CONNECTIONS = 5;

export function LiveModelCards({
  profiles,
  connections,
  teams,
  users,
  busy,
  onAdd,
  onConfigure,
  onManage,
  onRemove,
  onRetest,
}: {
  profiles: readonly LlmProfile[];
  connections: readonly LlmConnection[];
  teams: readonly Team[];
  users: readonly User[];
  busy: boolean;
  onAdd: () => void;
  onConfigure: (profile: LlmProfile) => void;
  onManage: () => void;
  onRemove: (profile: LlmProfile) => Promise<void>;
  onRetest: (profile: LlmProfile) => Promise<void>;
}) {
  const [removing, setRemoving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  return (
    <section aria-label="Live models" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Live models</h2>
          <p className="mt-1 text-sm text-muted">
            {profiles.length} of {MAX_MODEL_CONNECTIONS} connections · Assign one model to each
            audience.
          </p>
        </div>
        <Button disabled={busy || profiles.length >= MAX_MODEL_CONNECTIONS} onClick={onAdd}>
          Add model
        </Button>
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      <div className="flex snap-x gap-4 overflow-x-auto pb-3" aria-label="Configured model cards">
        {profiles.map((profile) => {
          const bindings = connections.filter((item) => item.profile_id === profile.id);
          const isDefault = bindings.some((item) => !item.user_id && !item.team_id);
          const teamNames = bindings.flatMap((item) =>
            item.team_id
              ? [teams.find((team) => team.id === item.team_id)?.name ?? 'Unavailable team']
              : [],
          );
          const userNames = bindings.flatMap((item) =>
            item.user_id
              ? [users.find((user) => user.id === item.user_id)?.display_name ?? 'Unavailable user']
              : [],
          );
          const legacy = connections.length === 0 && profile.enabled;
          const bound = bindings.length > 0 || legacy;
          return (
            <article
              key={profile.id}
              aria-label={`${profile.name} model card`}
              className={`flex w-[265px] shrink-0 snap-start flex-col rounded-xl border bg-surface/80 p-5 transition-colors hover:border-ember/60 motion-reduce:transition-none ${isDefault ? 'border-ember/70' : 'border-line'}`}
            >
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="text-muted">
                  {profile.provider === 'bedrock'
                    ? 'Amazon Bedrock'
                    : profile.base_url === 'https://api.openai.com/v1'
                      ? 'OpenAI'
                      : 'Custom provider'}
                </span>
                <span className={isDefault ? 'text-ember' : 'text-muted'}>
                  {isDefault
                    ? 'Default'
                    : legacy
                      ? 'Legacy active'
                      : bound
                        ? 'Assigned'
                        : profile.is_tested
                          ? 'Ready'
                          : 'Setup incomplete'}
                </span>
              </div>
              <h3 className="mt-4 break-words text-lg font-semibold">{profile.name}</h3>
              <p className="mt-1 break-all font-mono text-xs text-muted">{profile.model}</p>
              <p className="mt-2 text-xs capitalize">
                {profile.reasoning_effort ?? 'Provider default'} reasoning
              </p>
              <div className="my-4 min-h-24 flex-1 border-y border-line/70 py-3 text-sm">
                {isDefault && <p className="mb-2">Everyone without an override</p>}
                {legacy && (
                  <p className="text-muted">
                    Existing role-based model. Set a tested global default before changing it.
                  </p>
                )}
                {teamNames.length > 0 && (
                  <p className="text-muted">
                    Teams: <span className="text-text">{teamNames.join(', ')}</span>
                  </p>
                )}
                {userNames.length > 0 && (
                  <p className="mt-1 text-muted">
                    Users: <span className="text-text">{userNames.join(', ')}</span>
                  </p>
                )}
                {!bound && (
                  <p className="text-muted">
                    {profile.is_tested
                      ? 'Ready to assign to users or teams.'
                      : 'Finish setup and test this connection.'}
                  </p>
                )}
              </div>
              {removing === profile.id ? (
                <div className="space-y-2 text-sm">
                  <p>Remove this saved connection?</p>
                  <div className="flex gap-2">
                    <Button
                      disabled={busy}
                      onClick={() => {
                        setError(null);
                        void onRemove(profile)
                          .then(() => setRemoving(null))
                          .catch((failure: unknown) => setError(describeError(failure)));
                      }}
                    >
                      Confirm removal
                    </Button>
                    <Button disabled={busy} variant="ghost" onClick={() => setRemoving(null)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={bound ? onManage : () => onConfigure(profile)}
                  >
                    {bound ? 'Manage access' : profile.is_tested ? 'Assign model' : 'Finish setup'}
                  </Button>
                  {bound && !profile.is_tested && (
                    <Button
                      variant="ghost"
                      disabled={busy}
                      onClick={() => {
                        setError(null);
                        void onRetest(profile).catch((failure: unknown) =>
                          setError(describeError(failure)),
                        );
                      }}
                    >
                      Test connection
                    </Button>
                  )}
                  {!bound && (
                    <Button variant="ghost" disabled={busy} onClick={() => setRemoving(profile.id)}>
                      Remove
                    </Button>
                  )}
                </div>
              )}
            </article>
          );
        })}
        {profiles.length === 0 && (
          <button
            type="button"
            disabled={busy}
            onClick={onAdd}
            className="flex min-h-48 w-full items-center justify-center rounded-xl border border-dashed border-line text-sm text-muted transition-colors hover:border-ember hover:text-text disabled:opacity-50"
          >
            + Connect your first model
          </button>
        )}
      </div>
      {profiles.length >= MAX_MODEL_CONNECTIONS && (
        <p className="text-xs text-muted">
          All five slots are in use. Reassign any audiences, then remove an unused connection to
          free a slot.
        </p>
      )}
    </section>
  );
}
