import type { KeyboardEvent } from 'react';

import { SIDE_LABELS, type ForceNode } from '@/lib/api/ukraine';

import { ForcePortrait } from './ForcePortrait';
import { childrenOf, descendantCount, formatDate, isStale, type ForceTree } from './forceTree';
import './ukraineForces.css';

export type ChartLayout = 'chart' | 'stacked';

interface ChartProps {
  tree: ForceTree;
  open: ReadonlySet<string>;
  onToggle: (id: string) => void;
  selectedId: string | null;
  onSelect: (id: string) => void;
  layout: ChartLayout;
  retrievedAt: string;
  panelId: string;
  fetcher?: ((path: string) => Promise<Blob>) | undefined;
}

function NodeCard({ node, props }: { node: ForceNode; props: ChartProps }) {
  const { tree, open, onToggle, selectedId, onSelect, retrievedAt, panelId, fetcher } = props;
  const children = childrenOf(tree, node.id);
  const expanded = open.has(node.id);
  const selected = selectedId === node.id;
  const listId = `force-${tree.side}-${node.id}-children`;
  const hidden = expanded ? 0 : descendantCount(tree, node.id);
  const stale = isStale(node.as_of, retrievedAt);
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (children.length === 0) return;
    if (event.key === 'ArrowRight' && !expanded) onToggle(node.id);
    if (event.key === 'ArrowLeft' && expanded) onToggle(node.id);
  };
  return (
    <>
      <div
        className={`uk-org__node flex flex-col rounded-card border bg-surface text-left ${
          selected ? 'border-cyan bg-cyan/5' : 'border-line'
        }`}
      >
        <button
          type="button"
          onClick={() => onSelect(node.id)}
          onKeyDown={onKeyDown}
          aria-controls={panelId}
          aria-current={selected ? 'true' : undefined}
          className="flex min-h-11 w-full items-start gap-2 p-2 text-left hover:bg-surface-2"
        >
          {node.image_id ? (
            <ForcePortrait imageId={node.image_id} name={node.name} fetcher={fetcher} />
          ) : null}
          <span className="min-w-0 flex-1">
            <span className="block text-xs font-medium text-text">{node.name}</span>
            {node.commander ? (
              <span className="mt-0.5 block text-[11px] text-muted">{node.commander}</span>
            ) : null}
            {node.strength ? (
              <span className="mt-1 line-clamp-2 block text-[10px] text-muted">
                {node.strength}
              </span>
            ) : null}
          </span>
        </button>
        <p className="border-t border-line/60 px-2 py-1 font-mono text-[10px] text-muted">
          as of {formatDate(node.as_of)}
          {stale ? ' (may be out of date)' : ''}
        </p>
        {children.length > 0 ? (
          <button
            type="button"
            onClick={() => onToggle(node.id)}
            aria-expanded={expanded}
            aria-controls={listId}
            aria-label={`${expanded ? 'Collapse' : 'Expand'} ${node.name}, ${children.length} direct subordinate${children.length === 1 ? '' : 's'}`}
            className="min-h-9 border-t border-line/60 px-2 text-[11px] text-muted hover:text-text"
          >
            {expanded ? `Hide ${children.length}` : `Show ${children.length}`}
            <span aria-hidden="true">{expanded ? ' ▴' : ' ▾'}</span>
            {hidden > children.length ? (
              <span className="text-[10px]"> ({hidden} below)</span>
            ) : null}
          </button>
        ) : null}
      </div>
      {children.length > 0 ? (
        <ul id={listId} hidden={!expanded}>
          {children.map((child) => (
            <li key={child.id}>
              <NodeCard node={child} props={props} />
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}

/**
 * One side's command structure as a nested list. The same markup is a top-down chart with
 * connector lines on a wide screen and an indented outline on a narrow one, so there is only
 * ever one accessible tree rather than a picture plus a hidden copy of it.
 */
export function ForceChart(props: ChartProps) {
  const { tree, layout } = props;
  return (
    <div className={layout === 'chart' ? 'overflow-x-auto pb-2' : ''}>
      <div className="uk-org inline-block min-w-full" data-layout={layout}>
        <ul aria-label={`${SIDE_LABELS[tree.side]} chain of command`}>
          {tree.roots.map((root) => (
            <li key={root.id}>
              <NodeCard node={root} props={props} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
