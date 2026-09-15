import type { ReactNode } from 'react';

import { AdminIcon, type AdminGlyph } from './AdminIcon';

export type StatusTone = 'good' | 'warning' | 'critical' | 'info' | 'neutral';

const TONES: Record<StatusTone, { className: string; icon: AdminGlyph }> = {
  good: { className: 'border-good/40 bg-good/10 text-good', icon: 'check' },
  warning: { className: 'border-amber/45 bg-amber/10 text-amber', icon: 'alert' },
  critical: { className: 'border-critical/45 bg-critical/10 text-critical', icon: 'cross' },
  info: { className: 'border-cyan/40 bg-cyan/10 text-cyan', icon: 'clock' },
  neutral: { className: 'border-line bg-surface-2 text-muted', icon: 'pause' },
};

/** A status label that always pairs colour with an icon and readable text. */
export function StatusPill({
  tone,
  children,
  icon,
  className = '',
}: {
  tone: StatusTone;
  children: ReactNode;
  icon?: AdminGlyph;
  className?: string;
}) {
  const style = TONES[tone];
  return (
    <span
      data-tone={tone}
      className={`inline-flex max-w-full items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] leading-4 font-medium whitespace-nowrap ${style.className} ${className}`}
    >
      <AdminIcon name={icon ?? style.icon} size={12} />
      <span className="truncate">{children}</span>
    </span>
  );
}
