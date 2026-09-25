import type { ReactNode } from 'react';

export const CYBER_SECTIONS = [
  { id: 'cyber-overview', label: 'Overview' },
  { id: 'cyber-live', label: 'Live board' },
  { id: 'cyber-assessment', label: 'Assessment' },
  { id: 'cyber-focus', label: 'Focus areas' },
  { id: 'cyber-nation-state', label: 'Nation-state' },
  { id: 'cyber-gnss', label: 'GNSS' },
  { id: 'cyber-vulnerabilities', label: 'Vulnerabilities' },
  { id: 'cyber-actors', label: 'Actors' },
  { id: 'cyber-activity', label: 'Activity' },
  { id: 'cyber-briefing', label: 'Briefing' },
  { id: 'cyber-sources', label: 'Sources' },
] as const;

/** In-page jump links. Every section stays mounted; nothing is hidden behind a tab. */
export function CyberSectionNav({ preparing }: { preparing: boolean }) {
  return (
    <nav
      aria-label="Cyber workspace sections"
      className="sticky top-0 z-20 -mx-4 border-b border-line/60 bg-ground/85 px-4 py-2 backdrop-blur-md sm:-mx-7 sm:px-7 lg:-mx-10 lg:px-10"
    >
      <ul className="flex gap-1 overflow-x-auto text-xs whitespace-nowrap [scrollbar-width:thin]">
        {CYBER_SECTIONS.map((section) => (
          <li key={section.id}>
            <a
              href={`#${section.id}`}
              className="inline-flex min-h-9 items-center gap-2 rounded-md px-3 text-muted transition-colors hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
            >
              {section.label}
              {section.id === 'cyber-briefing' && preparing && (
                <span className="font-mono text-[10px] text-cyan">Preparing</span>
              )}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function SectionHeading({
  id,
  eyebrow,
  title,
  lede,
  aside,
}: {
  id: string;
  eyebrow: string;
  title: string;
  lede?: string | undefined;
  aside?: ReactNode | undefined;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-3xl">
        <p className="mb-1 font-mono text-[10px] tracking-[0.22em] text-cyan uppercase">
          {eyebrow}
        </p>
        <h2 id={`${id}-title`} className="text-xl font-semibold tracking-tight">
          {title}
        </h2>
        {lede && <p className="mt-2 text-sm leading-6 text-muted">{lede}</p>}
      </div>
      {aside}
    </div>
  );
}

/** One titled workspace section; the heading doubles as the jump-link target's label. */
export function Section({
  id,
  eyebrow,
  title,
  lede,
  aside,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  lede?: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-16 space-y-5">
      <SectionHeading id={id} eyebrow={eyebrow} title={title} lede={lede} aside={aside} />
      {children}
    </section>
  );
}
