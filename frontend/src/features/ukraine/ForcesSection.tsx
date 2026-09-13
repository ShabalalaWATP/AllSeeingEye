import { useMemo, useState } from 'react';
import { Link } from 'react-router';

import { SIDE_LABELS, type ForceNode, type Side, type UkraineReference } from '@/lib/api/ukraine';

function childrenOf(nodes: readonly ForceNode[], parent: string | null): ForceNode[] {
  return nodes.filter((node) => node.parent_id === parent);
}

function NodeCard({
  node,
  nodes,
  depth,
  open,
  toggle,
}: {
  node: ForceNode;
  nodes: readonly ForceNode[];
  depth: number;
  open: ReadonlySet<string>;
  toggle: (id: string) => void;
}) {
  const children = childrenOf(nodes, node.id);
  const expanded = open.has(node.id);
  return (
    <li className={depth > 0 ? 'ml-4 border-l border-line/60 pl-3' : ''}>
      <div className="rounded-card border border-line bg-surface p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <h4 className="font-medium text-text">{node.name}</h4>
            {node.commander ? (
              <p className="text-xs text-muted">
                Commander (reported): {node.commander}
                {node.figure_id ? (
                  <>
                    {' '}
                    <Link to="/trackers/figures" className="text-ember hover:underline">
                      figure record
                    </Link>
                  </>
                ) : null}
              </p>
            ) : null}
          </div>
          <span className="font-mono text-[10px] text-muted">as of {node.as_of}</span>
        </div>
        <p className="mt-1 text-sm text-muted">{node.role}</p>
        {node.strength ? (
          <p className="mt-1 text-xs text-muted">Strength: {node.strength}</p>
        ) : null}
        <div className="mt-1 flex flex-wrap items-center gap-3">
          {node.links.map((link) => (
            <a
              key={link.url}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-ember hover:underline"
            >
              {link.label}
            </a>
          ))}
          {children.length > 0 ? (
            <button
              type="button"
              aria-expanded={expanded}
              onClick={() => toggle(node.id)}
              className="min-h-9 rounded border border-line px-2 text-xs text-muted hover:text-text"
            >
              {expanded ? 'Hide' : 'Show'} {children.length} subordinate
              {children.length === 1 ? '' : 's'}
            </button>
          ) : null}
        </div>
      </div>
      {expanded && children.length > 0 ? (
        <ul className="mt-2 flex flex-col gap-2">
          {children.map((child) => (
            <NodeCard
              key={child.id}
              node={child}
              nodes={nodes}
              depth={depth + 1}
              open={open}
              toggle={toggle}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function Tree({ side, nodes }: { side: Side; nodes: readonly ForceNode[] }) {
  const own = useMemo(() => nodes.filter((node) => node.side === side), [nodes, side]);
  const [open, setOpen] = useState<ReadonlySet<string>>(
    () => new Set(own.filter((node) => node.parent_id === null).map((node) => node.id)),
  );
  const toggle = (id: string) =>
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  return (
    <section aria-label={`${SIDE_LABELS[side]} force structure`} className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-text">{SIDE_LABELS[side]}</h3>
      <ul className="flex flex-col gap-2">
        {childrenOf(own, null).map((root) => (
          <NodeCard key={root.id} node={root} nodes={own} depth={0} open={open} toggle={toggle} />
        ))}
      </ul>
    </section>
  );
}

/** Two expandable trees of reported command structure, each node dated and sourced. */
export function ForcesSection({ reference }: { reference: UkraineReference }) {
  return (
    <section id="forces" aria-labelledby="ukraine-forces-heading" className="flex flex-col gap-3">
      <h2 id="ukraine-forces-heading" className="text-base font-semibold">
        Force organisation
      </h2>
      <p className="max-w-3xl text-xs text-muted">
        Reported public structure, not an order of battle from observation. Commanders and strengths
        are as public reporting stated them on the date shown.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <Tree side="ru" nodes={reference.forces} />
        <Tree side="ua" nodes={reference.forces} />
      </div>
    </section>
  );
}
