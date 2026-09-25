/**
 * Page scaffolding shared by administration pages: one scroll container, a page
 * header with a single h1, and section cards with a clear heading hierarchy.
 */
import type { ReactNode } from 'react';

import { AdminIcon, type AdminGlyph } from './AdminIcon';
import './admin.css';

/** Card surface for sections that manage their own heading and landmark. */
export const ADMIN_CARD =
  'admin-rise min-w-0 rounded-card border border-line/80 bg-surface/70 p-4 sm:p-5';

const WIDTHS = { default: 'max-w-6xl', narrow: 'max-w-4xl', wide: 'max-w-7xl' } as const;

export function AdminPage({
  eyebrow,
  title,
  description,
  actions,
  meta,
  width = 'default',
  children,
}: {
  eyebrow: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  meta?: ReactNode;
  width?: keyof typeof WIDTHS;
  children: ReactNode;
}) {
  return (
    <section className="relative h-full min-w-0 overflow-x-hidden overflow-y-auto">
      <div
        aria-hidden="true"
        className="admin-grid-backdrop pointer-events-none absolute inset-x-0 top-0 h-56"
      />
      <div
        className={`relative mx-auto w-full ${WIDTHS[width]} px-4 pt-6 pb-24 sm:px-6 lg:px-10 lg:pt-9`}
      >
        <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4 border-b border-line/70 pb-6">
          <div className="min-w-0 max-w-3xl">
            <p className="font-mono text-2xs tracking-[0.22em] text-ember uppercase">
              {eyebrow}
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
              {title}
            </h1>
            {description === undefined ? null : (
              <div className="mt-2 text-sm leading-6 text-muted">{description}</div>
            )}
            {meta === undefined ? null : <div className="mt-3">{meta}</div>}
          </div>
          {actions === undefined ? null : (
            <div className="flex flex-wrap items-center gap-2">{actions}</div>
          )}
        </header>
        <div className="mt-6 space-y-6">{children}</div>
      </div>
    </section>
  );
}

/** A titled card. Pass `label` when the heading text differs from the landmark name. */
export function AdminSection({
  title,
  description,
  actions,
  label,
  icon,
  tone = 'default',
  children,
  className = '',
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  label?: string;
  icon?: AdminGlyph;
  tone?: 'default' | 'danger';
  children: ReactNode;
  className?: string;
}) {
  const border = tone === 'danger' ? 'border-critical/40' : 'border-line/80';
  return (
    <section
      aria-label={label ?? title}
      className={`admin-rise min-w-0 rounded-card border ${border} bg-surface/70 ${className}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line/60 px-4 py-3.5 sm:px-5">
        <div className="flex min-w-0 items-start gap-3">
          {icon === undefined ? null : (
            <span className="mt-0.5 flex size-8 items-center justify-center rounded-lg border border-line/80 bg-surface-2 text-ember">
              <AdminIcon name={icon} size={16} />
            </span>
          )}
          <div className="min-w-0">
            <h2 className="text-base font-semibold">{title}</h2>
            {description === undefined ? null : (
              <div className="mt-0.5 text-sm leading-6 text-muted">{description}</div>
            )}
          </div>
        </div>
        {actions === undefined ? null : (
          <div className="flex w-full flex-wrap gap-2 sm:w-auto">{actions}</div>
        )}
      </div>
      <div className="min-w-0 px-4 py-4 sm:px-5">{children}</div>
    </section>
  );
}

export function EmptyState({
  icon = 'check',
  title,
  children,
}: {
  icon?: AdminGlyph;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-line/80 px-4 py-8 text-center">
      <span className="flex size-10 items-center justify-center rounded-full bg-surface-2 text-muted">
        <AdminIcon name={icon} size={18} />
      </span>
      <p className="text-sm font-medium">{title}</p>
      {children === undefined ? null : (
        <div className="max-w-md text-sm text-muted">{children}</div>
      )}
    </div>
  );
}
