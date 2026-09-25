import { Link } from 'react-router';

import { SIDE_LABELS, type UkraineReference } from '@/lib/api/ukraine';

import { ancestryOf, childrenOf, formatDate, isStale, type ForceTree } from './forceTree';
import { ReferenceImage } from './ReferenceImage';

/** Detail for the node the reader focused in the chart, with its place in the chain of command. */
export function ForceNodeDetail({
  id,
  tree,
  nodeId,
  onSelect,
  reference,
  fetcher,
}: {
  id: string;
  tree: ForceTree;
  nodeId: string | null;
  onSelect: (id: string) => void;
  reference: UkraineReference;
  fetcher?: ((path: string) => Promise<Blob>) | undefined;
}) {
  const node = nodeId === null ? undefined : tree.byId.get(nodeId);
  if (node === undefined) {
    return (
      <aside
        id={id}
        aria-label={`${SIDE_LABELS[tree.side]} formation detail`}
        className="rounded-card border border-dashed border-line p-3 text-xs text-muted"
      >
        Choose a box in the chart to read the full entry, its place in the chain of command and its
        sources.
      </aside>
    );
  }
  const chain = ancestryOf(tree, node.id);
  const children = childrenOf(tree, node.id);
  const stale = isStale(node.as_of, reference.retrieved_at);
  return (
    <aside
      id={id}
      aria-label={`${SIDE_LABELS[tree.side]} formation detail`}
      className="flex flex-col gap-2 rounded-card border border-cyan/50 bg-surface p-3"
    >
      <nav aria-label="Chain of command" className="flex flex-wrap items-center gap-1">
        {chain.map((step, index) => (
          <span key={step.id} className="flex items-center gap-1">
            {index > 0 ? (
              <span aria-hidden="true" className="text-2xs text-muted">
                &gt;
              </span>
            ) : null}
            {step.id === node.id ? (
              <span className="text-[11px] text-text">{step.name}</span>
            ) : (
              <button
                type="button"
                onClick={() => onSelect(step.id)}
                className="min-h-8 text-[11px] text-ember hover:underline"
              >
                {step.name}
              </button>
            )}
          </span>
        ))}
      </nav>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h4 className="text-sm font-semibold text-text">{node.name}</h4>
        <span className="font-mono text-2xs text-muted">
          as of {formatDate(node.as_of)}
          {stale ? ' (may be out of date)' : ''}
        </span>
      </div>
      {node.image_id ? (
        <ReferenceImage
          imageId={node.image_id}
          meta={reference.images[node.image_id]}
          alt={node.commander ?? node.name}
          fetcher={fetcher}
          className="max-w-56"
        />
      ) : null}
      <p className="text-sm text-muted">{node.role}</p>
      {node.commander ? (
        <p className="text-xs text-muted">
          Commander (reported): <span className="text-text">{node.commander}</span>
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
      {node.strength ? (
        <p className="text-xs text-muted">
          <span className="text-text">Strength:</span> {node.strength}
        </p>
      ) : null}
      {children.length > 0 ? (
        <div className="flex flex-col gap-1">
          <h5 className="text-[11px] font-medium text-muted">
            Subordinate entries ({children.length})
          </h5>
          <ul className="flex flex-wrap gap-1">
            {children.map((child) => (
              <li key={child.id}>
                <button
                  type="button"
                  onClick={() => onSelect(child.id)}
                  className="min-h-8 rounded border border-line px-2 text-[11px] text-muted hover:text-text"
                >
                  {child.name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {node.links.length > 0 ? (
        <ul className="flex flex-wrap gap-3">
          {node.links.map((link) => (
            <li key={link.url}>
              <a
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-ember hover:underline"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[11px] text-muted">No public source link was resolved for this entry.</p>
      )}
    </aside>
  );
}
