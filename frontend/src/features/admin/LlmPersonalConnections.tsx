import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import type { User } from '@/lib/api/schemas';
import type { LlmConnection, LlmProfile } from '@/lib/api/llm';
export function LlmPersonalConnections({
  bindings,
  profiles,
  users,
  disabled,
  onReset,
  onReplace,
}: {
  bindings: LlmConnection[];
  profiles: LlmProfile[];
  users: User[];
  disabled: boolean;
  onReset: (userId: string) => void;
  onReplace: (profile: LlmProfile, userId: string) => void;
}) {
  const [confirm, setConfirm] = useState<string | null>(null);
  const personal = bindings.filter((item) => item.user_id);
  return (
    <section aria-label="Personal AI overrides" className="border-b border-line pb-5">
      <details open={personal.length > 0} className="space-y-3">
        <summary className="cursor-pointer text-sm font-medium">
          Personal workspace overrides <span className="ml-2 text-muted">{personal.length}</span>
        </summary>
        <p className="text-sm text-muted">
          These apply only to the named personal workspace. Team research follows the team or global
          connection.
        </p>
        {personal.length === 0 ? (
          <p className="text-sm text-muted">
            No personal overrides. Personal research uses the global connection.
          </p>
        ) : (
          <ul className="divide-y divide-line">
            {personal.map((binding) => {
              const user = users.find((entry) => entry.id === binding.user_id);
              const profile = profiles.find((entry) => entry.id === binding.profile_id);
              return (
                <li key={binding.user_id} className="space-y-2 py-3">
                  <p className="text-sm font-medium">
                    {user?.email ?? 'User unavailable'}
                    {user && !user.is_active && ' (inactive)'}
                  </p>
                  <p className="font-mono text-sm">
                    {profile?.model ?? 'Connection unavailable'} -{' '}
                    {profile?.reasoning_effort ?? 'provider default'}
                  </p>
                  <div className="flex gap-2">
                    {profile && (
                      <Button
                        variant="secondary"
                        disabled={disabled}
                        onClick={() => {
                          if (binding.user_id) onReplace(profile, binding.user_id);
                        }}
                      >
                        Replace personal connection
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      disabled={disabled}
                      onClick={() => setConfirm(binding.user_id ?? null)}
                    >
                      Use global connection
                    </Button>
                  </div>
                  {confirm === binding.user_id && (
                    <div className="space-y-2">
                      <p className="text-sm">
                        Reset this personal workspace to the global AI connection?
                      </p>
                      <Button
                        disabled={disabled}
                        onClick={() => {
                          if (binding.user_id) onReset(binding.user_id);
                        }}
                      >
                        Confirm personal reset
                      </Button>
                      <Button variant="ghost" onClick={() => setConfirm(null)}>
                        Keep personal override
                      </Button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </details>
    </section>
  );
}
