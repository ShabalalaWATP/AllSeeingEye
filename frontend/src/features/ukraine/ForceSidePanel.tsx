import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useReducedMotion } from '@/components/brand/useMotionPreferences';
import { SIDE_LABELS, type ForceNode, type Side, type UkraineReference } from '@/lib/api/ukraine';

import { ForceChart, type ChartLayout } from './ForceChart';
import { ForceNodeDetail } from './ForceNodeDetail';
import {
  allBranchIds,
  buildForceTree,
  openToLevel,
  DEFAULT_OPEN_LEVELS,
  type ForceTree,
} from './forceTree';

/** How many matching units a search lists before asking for a narrower term. */
const MAX_MATCHES = 8;

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

/** Units whose name or commander contains every word of the query, in catalogue order. */
export function matchUnits(tree: ForceTree, query: string): ForceNode[] {
  const words = query.toLocaleLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return [];
  const hits: ForceNode[] = [];
  for (const node of tree.byId.values()) {
    const text = `${node.name} ${node.commander ?? ''}`.toLocaleLowerCase();
    if (words.every((word) => text.includes(word))) hits.push(node);
  }
  return hits;
}

/** One side of the comparison: its chart, a unit search, its expand controls and its detail panel. */
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
  const [query, setQuery] = useState('');
  const panelId = `force-detail-${side}`;
  const reduceMotion = useReducedMotion();
  const detail = useRef<HTMLDivElement>(null);
  const total = tree.byId.size;
  const branches = useMemo(() => allBranchIds(tree), [tree]);
  const allOpen = branches.size > 0 && [...branches].every((id) => open.has(id));
  const matches = useMemo(() => matchUnits(tree, query), [tree, query]);

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
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-muted">
            <span>Find a unit</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="e.g. 47th or Azov"
              className="min-h-9 w-44 rounded border border-line bg-ground px-2 text-xs text-text"
            />
          </label>
          <button
            type="button"
            onClick={() => setOpen(allOpen ? openToLevel(tree, DEFAULT_OPEN_LEVELS) : branches)}
            className="min-h-9 rounded border border-line px-2 text-xs text-muted hover:text-text"
          >
            {allOpen ? 'Collapse' : 'Expand all'}
          </button>
        </div>
      </div>
      {query.trim() !== '' && (
        <div role="status" className="text-xs text-muted">
          {matches.length === 0 ? (
            <p>No unit on this side matches.</p>
          ) : (
            <ul
              aria-label={`${SIDE_LABELS[side]} units matching the search`}
              className="flex flex-wrap gap-1"
            >
              {matches.slice(0, MAX_MATCHES).map((node) => (
                <li key={node.id}>
                  <button
                    type="button"
                    onClick={() => select(node.id)}
                    className="min-h-9 rounded-full border border-line px-3 text-xs text-text hover:border-cyan"
                  >
                    {node.name}
                  </button>
                </li>
              ))}
              {matches.length > MAX_MATCHES && (
                <li className="self-center">
                  and {matches.length - MAX_MATCHES} more; narrow the search
                </li>
              )}
            </ul>
          )}
        </div>
      )}
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
