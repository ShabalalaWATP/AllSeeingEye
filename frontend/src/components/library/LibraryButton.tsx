import { useCallback, useState } from 'react';
import { useAccountRequest } from '@/components/account/useAccountRequest';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField, TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import {
  fetchLibraryPreference,
  saveLibraryPreference,
  removeLibraryPreference,
} from '@/lib/api/researchLibrary';
import type { LibraryPreference } from '@/lib/api/researchLibrary';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

export function LibraryButton({
  reportId,
  onChanged,
}: {
  reportId: string;
  onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2">
      <Button variant="ghost" onClick={() => setOpen(!open)}>
        {open ? 'Close library settings' : 'Save / organise'}
      </Button>
      {open && (
        <LibraryLoader reportId={reportId} onChanged={onChanged} onClose={() => setOpen(false)} />
      )}
    </div>
  );
}

function LibraryLoader({
  reportId,
  onChanged,
  onClose,
}: {
  reportId: string;
  onChanged: () => void;
  onClose: () => void;
}) {
  const resource = useScopedResource(
    useCallback(() => fetchLibraryPreference(reportId), [reportId]),
  );
  return (
    <div className="mt-3 space-y-3 rounded border border-line p-4">
      {resource.loading && <p role="status">Loading personal library settings...</p>}
      {resource.error && (
        <>
          <Alert tone="error">{describeError(resource.error)}</Alert>
          <Button variant="secondary" onClick={() => void resource.reload()}>
            Retry library settings
          </Button>
        </>
      )}
      {resource.data && (
        <LibraryEditor
          key={resource.key}
          initial={resource.data}
          reportId={reportId}
          onChanged={onChanged}
          onClose={onClose}
        />
      )}
    </div>
  );
}

function LibraryEditor({
  initial,
  reportId,
  onChanged,
  onClose,
}: {
  initial: LibraryPreference;
  reportId: string;
  onChanged: () => void;
  onClose: () => void;
}) {
  const [favourite, setFavourite] = useState(initial.favourite);
  const [tags, setTags] = useState(initial.tags.join(', '));
  const [note, setNote] = useState(initial.note ?? '');
  const [removing, setRemoving] = useState(false);
  const begin = useAccountRequest();
  const action = useAsyncAction(async (remove: boolean) => {
    const signal = begin();
    if (remove) await removeLibraryPreference(reportId, signal);
    else
      await saveLibraryPreference(
        reportId,
        {
          favourite,
          tags: tags
            .split(',')
            .map((tag) => tag.trim())
            .filter(Boolean),
          note: note || null,
        },
        signal,
      );
    if (signal.aborted) return;
    onChanged();
    onClose();
  });
  return (
    <form
      aria-label="Personal library settings"
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!action.busy) void action.run(false);
      }}
    >
      <p className="text-xs text-muted">
        Only you can see these tags and notes. Saving does not change report sharing or its frozen
        contents.
      </p>
      {action.error && <Alert tone="error">{describeError(action.error)}</Alert>}
      <fieldset disabled={action.busy} className="space-y-3">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={favourite}
            onChange={(event) => setFavourite(event.target.checked)}
          />
          Favourite
        </label>
        <TextField
          label="Tags, separated by commas"
          value={tags}
          maxLength={502}
          hint="Up to 12 unique tags, 40 characters each."
          onChange={(event) => setTags(event.target.value)}
        />
        <TextAreaField
          label="Private note"
          value={note}
          maxLength={1000}
          onChange={(event) => setNote(event.target.value)}
        />
      </fieldset>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" busy={action.busy}>
          Save to my library
        </Button>
        {initial.updated_at && (
          <Button variant="ghost" disabled={action.busy} onClick={() => setRemoving(true)}>
            Remove from my library
          </Button>
        )}
      </div>
      {removing && (
        <div className="space-y-2 border-t border-line pt-3">
          <p className="text-sm">
            Remove your tags, favourite and note? The report will remain available wherever you have
            access.
          </p>
          <Button variant="danger" busy={action.busy} onClick={() => void action.run(true)}>
            Confirm removal
          </Button>
        </div>
      )}
    </form>
  );
}
