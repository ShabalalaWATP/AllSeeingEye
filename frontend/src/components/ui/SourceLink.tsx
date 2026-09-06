import type { ReactNode } from 'react';
import { isHttpUrl } from '@/lib/urls';

/** Captured URLs remain untrusted, including declared identity and publisher links. */
export function SourceLink({ url, children }: { url: string | null; children: ReactNode }) {
  if (!isHttpUrl(url)) return null;
  const parsed = new URL(url);
  if (
    parsed.username ||
    parsed.password ||
    Array.from(url).some(
      (character) => character.charCodeAt(0) <= 32 || character.charCodeAt(0) === 127,
    )
  )
    return null;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-ember underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
    >
      {children}
    </a>
  );
}
