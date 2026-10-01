import type { ReactNode, Ref } from 'react';

/**
 * The kind of page a heading names. Each kind has one heading size, so pages of the same
 * kind look alike: a workspace or sign-in page, a single record or tool, or a status page
 * such as "not found".
 */
export type PageType = 'workspace' | 'record' | 'status';

const TITLE: Record<PageType, string> = {
  workspace: 'text-3xl font-semibold tracking-tight text-balance',
  record: 'text-xl font-semibold',
  status: 'text-2xl font-semibold',
};

const EYEBROW_TONE = { ember: 'text-ember', cyan: 'text-cyan', muted: 'text-muted' } as const;

export interface PageHeaderProps {
  title: ReactNode;
  type?: PageType | undefined;
  /** A short label above the title naming the area, such as "Shared workspaces". */
  eyebrow?: ReactNode;
  eyebrowTone?: keyof typeof EYEBROW_TONE | undefined;
  /** A way back, such as a link to the parent list, shown above everything else. */
  back?: ReactNode;
  /** Short facts beside the title, such as a status badge. */
  titleAside?: ReactNode;
  description?: ReactNode;
  /** Further header content below the description: links, metadata, summary figures. */
  children?: ReactNode;
  /** Page-level actions, placed at the end of the header. */
  actions?: ReactNode;
  /** `div` when the caller already provides the surrounding `header`. */
  as?: 'header' | 'div' | undefined;
  className?: string | undefined;
  headingId?: string | undefined;
  headingRef?: Ref<HTMLHeadingElement> | undefined;
  /** Lets the page move focus to its heading, for example after a step change. */
  focusable?: boolean | undefined;
}

/** The page's one `h1` and what introduces it. Every route page names itself through this. */
export function PageHeader({
  title,
  type = 'workspace',
  eyebrow,
  eyebrowTone = 'ember',
  back,
  titleAside,
  description,
  children,
  actions,
  as: Tag = 'header',
  className = '',
  headingId,
  headingRef,
  focusable = false,
}: PageHeaderProps) {
  const heading = (
    <h1
      ref={headingRef}
      id={headingId}
      tabIndex={focusable ? -1 : undefined}
      className={TITLE[type]}
    >
      {title}
    </h1>
  );
  return (
    <Tag className={`flex flex-wrap items-end justify-between gap-x-6 gap-y-4 ${className}`}>
      <div className={`flex min-w-0 flex-col gap-2 ${type === 'workspace' ? 'max-w-3xl' : ''}`}>
        {back}
        {eyebrow === undefined ? null : (
          <p
            className={`font-mono text-2xs tracking-[0.22em] uppercase ${EYEBROW_TONE[eyebrowTone]}`}
          >
            {eyebrow}
          </p>
        )}
        {titleAside === undefined ? (
          heading
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            {heading}
            {titleAside}
          </div>
        )}
        {description === undefined ? null : (
          <div className="text-sm leading-6 text-muted">{description}</div>
        )}
        {children}
      </div>
      {actions === undefined ? null : (
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      )}
    </Tag>
  );
}
