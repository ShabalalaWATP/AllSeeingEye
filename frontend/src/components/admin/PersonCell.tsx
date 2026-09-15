/** Name and email with decorative initials, for dense administration tables. */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0], parts.at(-1)] : [parts[0]];
  return letters
    .map((part) => part?.charAt(0) ?? '')
    .join('')
    .toUpperCase();
}

export function PersonCell({
  name,
  email,
  muted = false,
}: {
  name: string;
  email: string;
  muted?: boolean;
}) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span
        aria-hidden="true"
        className={`flex size-9 shrink-0 items-center justify-center rounded-full border font-mono text-[11px] font-semibold ${muted ? 'border-line bg-surface-2 text-muted' : 'border-ember/40 bg-ember/10 text-ember'}`}
      >
        {initials(name)}
      </span>
      <div className="min-w-0">
        <div className="truncate font-medium">{name}</div>
        <div className="truncate text-xs text-muted">{email}</div>
      </div>
    </div>
  );
}
