/**
 * Pure helpers for the force organisation chart: one side's nodes arranged as a tree,
 * with the ancestry, counts and staleness the chart and its detail panel need.
 */
import type { ForceNode, Side } from '@/lib/api/ukraine';

export interface ForceTree {
  readonly side: Side;
  readonly roots: readonly ForceNode[];
  readonly byId: ReadonlyMap<string, ForceNode>;
  readonly children: ReadonlyMap<string, readonly ForceNode[]>;
  readonly depth: ReadonlyMap<string, number>;
}

/** Levels opened when the chart first renders: enough to show the chain of command. */
export const DEFAULT_OPEN_LEVELS = 3;
/** Entries older than this are marked as possibly out of date rather than silently trusted. */
const STALE_AFTER_DAYS = 365;

/**
 * Groups one side's nodes by parent. A node whose parent belongs to the other side, or is
 * missing, is treated as a root so nothing is dropped from the display.
 */
export function buildForceTree(nodes: readonly ForceNode[], side: Side): ForceTree {
  const own = nodes.filter((node) => node.side === side);
  const byId = new Map(own.map((node) => [node.id, node]));
  const children = new Map<string, ForceNode[]>();
  const roots: ForceNode[] = [];
  for (const node of own) {
    const parent = node.parent_id !== null && byId.has(node.parent_id) ? node.parent_id : null;
    if (parent === null) roots.push(node);
    else children.set(parent, [...(children.get(parent) ?? []), node]);
  }
  const depth = new Map<string, number>();
  const walk = (node: ForceNode, level: number): void => {
    depth.set(node.id, level);
    for (const child of children.get(node.id) ?? []) walk(child, level + 1);
  };
  for (const root of roots) walk(root, 0);
  return { side, roots, byId, children, depth };
}

export function childrenOf(tree: ForceTree, id: string): readonly ForceNode[] {
  return tree.children.get(id) ?? [];
}

/** The chain from the root down to the node, the node itself last. */
export function ancestryOf(tree: ForceTree, id: string): readonly ForceNode[] {
  const chain: ForceNode[] = [];
  let current = tree.byId.get(id);
  while (current) {
    chain.unshift(current);
    const parent = current.parent_id;
    current = parent === null ? undefined : tree.byId.get(parent);
    if (current && chain.some((node) => node.id === current?.id)) break;
  }
  return chain;
}

/** Everything below a node, so a collapsed branch can say how much it is hiding. */
export function descendantCount(tree: ForceTree, id: string): number {
  const direct = childrenOf(tree, id);
  return direct.reduce((total, child) => total + 1 + descendantCount(tree, child.id), 0);
}

export function branchIds(tree: ForceTree, id: string): string[] {
  return childrenOf(tree, id).flatMap((child) => [child.id, ...branchIds(tree, child.id)]);
}

/** Ids that should start expanded: every node with children above the given level. */
export function openToLevel(tree: ForceTree, levels: number): Set<string> {
  const open = new Set<string>();
  for (const [id, level] of tree.depth) {
    if (level < levels && childrenOf(tree, id).length > 0) open.add(id);
  }
  return open;
}

export function allBranchIds(tree: ForceTree): Set<string> {
  return new Set([...tree.depth.keys()].filter((id) => childrenOf(tree, id).length > 0));
}

/** True when the entry's as-of date is more than a year before the catalogue was built. */
export function isStale(asOf: string, retrievedAt: string): boolean {
  const entry = Date.parse(asOf);
  const reference = Date.parse(retrievedAt);
  if (Number.isNaN(entry) || Number.isNaN(reference)) return false;
  return reference - entry > STALE_AFTER_DAYS * 24 * 60 * 60 * 1000;
}

export function formatDate(value: string): string {
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });
}
