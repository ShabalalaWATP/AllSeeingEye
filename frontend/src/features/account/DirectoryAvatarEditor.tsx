import { useRef, useState } from 'react';

import { DirectoryAvatar } from '@/components/account/DirectoryAvatar';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { asApiError, describeError } from '@/lib/api/errors';
import {
  AVATAR_TYPES,
  MAX_AVATAR_BYTES,
  removeDirectoryAvatar,
  uploadDirectoryAvatar,
  type DirectoryProfile,
} from '@/lib/api/directoryProfile';

const acceptedTypes: readonly string[] = AVATAR_TYPES;

export function DirectoryAvatarEditor({
  profile,
  name,
  disabled,
  onChange,
}: {
  profile: DirectoryProfile;
  name: string;
  disabled: boolean;
  onChange: (profile: DirectoryProfile) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<DirectoryProfile>) {
    setBusy(true);
    setError(null);
    try {
      onChange(await action());
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
      if (input.current) input.current.value = '';
    }
  }

  function choose(file: File | undefined) {
    if (!file) return;
    if (!acceptedTypes.includes(file.type)) {
      setError('Choose a JPEG, PNG or WebP image.');
      return;
    }
    if (file.size > MAX_AVATAR_BYTES) {
      setError('Avatar images must be 2 MB or smaller.');
      return;
    }
    void run(() => uploadDirectoryAvatar(file));
  }

  const locked = disabled || busy;
  return (
    <section aria-labelledby="directory-avatar-heading" className="flex flex-col gap-3">
      <h3 id="directory-avatar-heading" className="text-sm font-medium">
        Avatar
      </h3>
      <div className="flex flex-wrap items-center gap-4">
        <DirectoryAvatar avatarUrl={profile.avatar_url} name={name} size={64} />
        <label className="text-sm">
          <span className="sr-only">Upload avatar image</span>
          <input
            ref={input}
            type="file"
            accept={AVATAR_TYPES.join(',')}
            disabled={locked}
            className="text-xs file:mr-3 file:border file:border-line file:bg-surface-2 file:px-3 file:py-1.5"
            onChange={(event) => choose(event.target.files?.[0])}
          />
        </label>
        {profile.avatar_url ? (
          <Button
            variant="ghost"
            busy={busy}
            disabled={locked}
            onClick={() => void run(removeDirectoryAvatar)}
          >
            Remove avatar
          </Button>
        ) : null}
      </div>
      <p className="text-xs text-muted">
        JPEG, PNG or WebP up to 2 MB. It is resized and its metadata, such as location, is removed.
        Teammates and, when you are discoverable, directory users can see it.
      </p>
      {error ? <Alert tone="error">{error}</Alert> : null}
    </section>
  );
}
