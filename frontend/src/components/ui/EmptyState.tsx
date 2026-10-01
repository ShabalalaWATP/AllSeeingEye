import type { ReactNode } from 'react';

/**
 * An empty list that says what the list is for and the first thing to do, so a new
 * analyst learns the purpose of a workspace from the workspace itself.
 */
export function EmptyState({
  title,
  purpose,
  action,
}: {
  title: string;
  purpose: string;
  action: ReactNode;
}) {
  return (
    <div className="rounded-card border border-dashed border-line px-4 py-4 text-sm">
      <p className="font-medium text-text">{title}</p>
      <p className="mt-1 leading-6 text-muted">{purpose}</p>
      <p className="mt-2 text-text">{action}</p>
    </div>
  );
}
