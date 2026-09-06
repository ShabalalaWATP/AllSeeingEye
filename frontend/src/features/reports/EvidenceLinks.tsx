import { createContext, useContext, type ReactNode } from 'react';

import type { EvidenceItem } from '@/lib/api/reports';

const EvidenceLabels = createContext<ReadonlySet<string>>(new Set());

export function evidenceId(label: string): string {
  return `evidence-${encodeURIComponent(label)}`;
}

export function EvidenceNavigation({
  evidence,
  children,
}: {
  evidence: readonly EvidenceItem[];
  children: ReactNode;
}) {
  return (
    <EvidenceLabels value={new Set(evidence.map((item) => item.label))}>{children}</EvidenceLabels>
  );
}

/** Citation activation opens and focuses the matching native disclosure. */
export function Labels({ labels }: { labels: readonly string[] }) {
  const available = useContext(EvidenceLabels);
  if (labels.length === 0) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-middle">
      {[...new Set(labels)].map((label) =>
        available.has(label) ? (
          <a
            key={label}
            href={`#${encodeURIComponent(evidenceId(label))}`}
            aria-label={`View evidence ${label}`}
            className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-ember transition-colors hover:bg-ember/15 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember motion-reduce:transition-none"
            onClick={(event) => {
              const target = event.currentTarget.ownerDocument.getElementById(evidenceId(label));
              if (target instanceof HTMLDetailsElement) {
                target.open = true;
                target.querySelector('summary')?.focus();
              }
            }}
          >
            {label}
          </a>
        ) : (
          <span
            key={label}
            className="rounded bg-surface-2 px-1 font-mono text-[11px] text-muted"
            title="Evidence is not available in this view"
          >
            {label}
          </span>
        ),
      )}
    </span>
  );
}
