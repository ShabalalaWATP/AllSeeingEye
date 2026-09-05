import { useCallback, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { createLlmProfile, fetchLlmProfiles, updateLlmProfile } from '@/lib/api/llm';
import type { LlmProfile, LlmProfileInput } from '@/lib/api/llm';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';

import { LlmProfileForm } from './LlmProfileForm';
import { LlmProfileRow } from './LlmProfileRow';

type Editor = { mode: 'closed' } | { mode: 'create' } | { mode: 'edit'; profile: LlmProfile };

export default function AdminLlmPage() {
  const { data, error, loading, setData } = useResource(fetchLlmProfiles);
  const [editor, setEditor] = useState<Editor>({ mode: 'closed' });

  const upsert = useCallback(
    (profile: LlmProfile) => {
      setData((current) => {
        if (current === null) return current;
        const exists = current.items.some((item) => item.id === profile.id);
        const items = exists
          ? current.items.map((item) => (item.id === profile.id ? profile : item))
          : [...current.items, profile];
        return { ...current, items };
      });
    },
    [setData],
  );

  const removed = useCallback(
    (id: string) => {
      setData((current) =>
        current === null
          ? current
          : { ...current, items: current.items.filter((item) => item.id !== id) },
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
  });

  const encryption = data?.encryption_available ?? true;

  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">Models</h1>
        {editor.mode === 'closed' && (
          <Button
            onClick={() => {
              save.clearError();
              setEditor({ mode: 'create' });
            }}
            disabled={!encryption}
          >
            New profile
          </Button>
        )}
      </div>
      {encryption ? null : (
        <Alert tone="warning" title="Keys cannot be stored">
          Set ASE_ENCRYPTION_KEY on the server (any 32 or more random characters) and restart it
          before adding model profiles. Existing profiles cannot be tested until then.
        </Alert>
      )}
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      {editor.mode !== 'closed' && (
        <LlmProfileForm
          key={editor.mode === 'edit' ? editor.profile.id : 'new'}
          initial={editor.mode === 'edit' ? editor.profile : undefined}
          busy={save.busy}
          error={save.error === null ? null : describeError(save.error)}
          onSubmit={(input) => void save.run(input)}
          onCancel={() => {
            save.clearError();
            setEditor({ mode: 'closed' });
          }}
        />
      )}
      {data === null ? (
        loading ? (
          <LoadingNote label="Loading model profiles" />
        ) : null
      ) : data.items.length === 0 ? (
        <p className="text-sm text-muted">
          No model profiles yet. Add an OpenAI-compatible endpoint to enable report generation.
        </p>
      ) : (
        <Table caption="Model profiles">
          <thead>
            <tr>
              <Th>Profile</Th>
              <Th>Key</Th>
              <Th>Roles</Th>
              <Th>Status</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((profile) => (
              <LlmProfileRow
                key={profile.id}
                profile={profile}
                onEdit={(target) => {
                  save.clearError();
                  setEditor({ mode: 'edit', profile: target });
                }}
                onDeleted={removed}
              />
            ))}
          </tbody>
        </Table>
      )}
    </section>
  );
}
