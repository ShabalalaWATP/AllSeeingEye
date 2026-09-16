import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useReducedMotion } from '@/components/brand/useMotionPreferences';
import { SIDE_LABELS, type Side, type UkraineReference } from '@/lib/api/ukraine';

import { ForceChart, type ChartLayout } from './ForceChart';
import { ForceNodeDetail } from './ForceNodeDetail';
import {
  allBranchIds,
  buildForceTree,
  openToLevel,
  DEFAULT_OPEN_LEVELS,
  type ForceTree,
} from './forceTree';

function useOpenBranches(tree: ForceTree) {
  const [open, setOpen] = useState<ReadonlySet<string>>(() =>
    openToLevel(tree, DEFAULT_OPEN_LEVELS),
  );
  const toggle = useCallback((id: string) => {
    setOpen((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }, []);
  return { open, setOpen, toggle };
}

/** One side of the comparison: its chart, its expand controls and its detail panel. */
export function ForceSidePanel({
  side,
  reference,
  layout,
  fetcher,
}: {
  side: Side;
  reference: UkraineReference;
  layout: ChartLayout;
  fetcher?: ((path: string) => Promise<Blob>) | undefined;
}) {
  const tree = useMemo(() => buildForceTree(reference.forces, side), [reference.forces, side]);
  const { open, setOpen, toggle } = useOpenBranches(tree);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const panelId = `force-detail-${side}`;
  const reduceMotion = useReducedMotion();
  const detail = useRef<HTMLDivElement>(null);
  const total = tree.byId.size;
  const branches = useMemo(() => allBranchIds(tree), [tree]);
  const allOpen = branches.size > 0 && [...branches].every((id) => open.has(id));

  const select = useCallback(
    (id: string) => {
      setSelectedId(id);
      setOpen((current) => {
        if (current.has(id)) return current;
        const next = new Set(current);
        let walk = tree.byId.get(id)?.parent_id ?? null;
        while (walk !== null) {
          next.add(walk);
          walk = tree.byId.get(walk)?.parent_id ?? null;
        }
        return next;
      });
    },
    [setOpen, tree],
  );

  useEffect(() => {
    if (selectedId === null || detail.current === null) return;
    detail.current.scrollIntoView({
      block: 'nearest',
      behavior: reduceMotion ? 'auto' : 'smooth',
    });
  }, [selectedId, reduceMotion]);

  return (
    <section
      aria-label={`${SIDE_LABELS[side]} force structure`}
      className="flex min-w-0 flex-col gap-2"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-text">
          {SIDE_LABELS[side]}{' '}
          <span className="font-mono text-[11px] font-normal text-muted">({total} entries)</span>
        </h3>
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setOpen(allOpen ? openToLevel(tree, DEFAULT_OPEN_LEVELS) : branches)}
            className="min-h-9 rounded border border-line px-2 text-xs text-muted hover:text-text"
          >
            {allOpen ? 'Collapse' : 'Expand all'}
          </button>
        </div>
      </div>
      <ForceChart
        tree={tree}
        open={open}
        onToggle={toggle}
        selectedId={selectedId}
        onSelect={select}
        layout={layout}
        retrievedAt={reference.retrieved_at}
        panelId={panelId}
        fetcher={fetcher}
      />
      <div ref={detail}>
        <ForceNodeDetail
          id={panelId}
          tree={tree}
          nodeId={selectedId}
          onSelect={select}
          reference={reference}
          fetcher={fetcher}
        />
      </div>
    </section>
  );
}
