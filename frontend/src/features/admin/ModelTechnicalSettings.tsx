import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { createLlmProfile, updateLlmProfile } from '@/lib/api/llm';
import type { LlmProfile, LlmProfileInput } from '@/lib/api/llm';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { LlmProfileForm } from './LlmProfileForm';

/** Embeddings remain separate from the five research model slots. */
export function ModelTechnicalSettings({
  profiles,
  onSaved,
  onBusyChange,
}: {
  profiles: readonly LlmProfile[];
  onSaved: (profile: LlmProfile) => void;
  onBusyChange?: (busy: boolean) => void;
}) {
  const [editor, setEditor] = useState<LlmProfile | 'new' | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const request = useScopedRequest();
  const save = async (input: LlmProfileInput) => {
    if (busy) return false;
    const signal = request();
    setBusy(true);
    onBusyChange?.(true);
    setError(null);
    try {
      const saved =
        editor && editor !== 'new'
          ? await updateLlmProfile(editor.id, input, signal)
          : await createLlmProfile(input, signal);
      signal.throwIfAborted();
      onSaved(saved);
      setEditor(null);
      return true;
    } catch (failure) {
      if (!signal.aborted) setError(describeError(failure));
      return false;
    } finally {
      if (!signal.aborted) setBusy(false);
      onBusyChange?.(false);
    }
  };
  return (
    <section aria-label="Embedding connections" className="space-y-3 border-t border-line pt-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold">Embedding connections</h3>
          <p className="text-xs text-muted">
            Technical search profiles, separate from research models.
          </p>
        </div>
        {!editor && (
          <Button variant="secondary" onClick={() => setEditor('new')}>
            Add embedding connection
          </Button>
        )}
      </div>
      {editor ? (
        <LlmProfileForm
          key={typeof editor === 'string' ? 'new' : editor.id}
          embeddingsOnly
          {...(editor !== 'new' ? { initial: editor } : {})}
          busy={busy}
          error={error}
          onSubmit={save}
          onCancel={() => {
            setEditor(null);
            setError(null);
          }}
        />
      ) : (
        profiles
          .filter((profile) => profile.roles.includes('embeddings'))
          .map((profile) => (
            <div key={profile.id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span>
                {profile.name} <span className="text-muted">{profile.model}</span>
              </span>
              <Button variant="ghost" onClick={() => setEditor(profile)}>
                Edit {profile.name}
              </Button>
            </div>
          ))
      )}
    </section>
  );
}
