import { useEffect, useState } from 'react';

import { fetchDirectoryAvatar } from '@/lib/api/directoryProfile';

function initials(name: string): string {
  const letters = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
  return letters || '?';
}

/**
 * Shows a directory avatar fetched with the session token, falling back to initials.
 * The server re-encodes every avatar, and the image is only ever rendered as a blob URL.
 */
export function DirectoryAvatar({
  avatarUrl,
  name,
  size = 40,
}: {
  avatarUrl: string | null;
  name: string;
  size?: number;
}) {
  const [loaded, setLoaded] = useState<{ source: string; objectUrl: string } | null>(null);

  useEffect(() => {
    if (avatarUrl === null) return;
    const controller = new AbortController();
    let objectUrl: string | null = null;
    fetchDirectoryAvatar(avatarUrl, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setLoaded({ source: avatarUrl, objectUrl });
      })
      .catch(() => {
        // A missing or no longer visible avatar falls back to initials.
      });
    return () => {
      controller.abort();
      if (objectUrl !== null) URL.revokeObjectURL(objectUrl);
    };
  }, [avatarUrl]);

  const style = { width: size, height: size };
  if (avatarUrl !== null && loaded?.source === avatarUrl) {
    return (
      <img
        src={loaded.objectUrl}
        alt={`Avatar for ${name}`}
        width={size}
        height={size}
        style={style}
        className="shrink-0 rounded-full border border-line object-cover"
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      style={style}
      className="inline-flex shrink-0 items-center justify-center rounded-full border border-line bg-surface-2 font-mono text-xs text-muted"
    >
      {initials(name)}
    </span>
  );
}
