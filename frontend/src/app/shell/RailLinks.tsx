import { Link, useLocation } from 'react-router';

import {
  containsWorkspacePath,
  isWorkspacePath,
  type WorkspaceDestination,
} from '@/lib/workspaceNavigation';

import { RailIcon } from './railIcons';

interface RailLinkProps {
  item: WorkspaceDestination;
  collapsed: boolean;
  onNavigate?: (() => void) | undefined;
}

function linkClass(active: boolean, sectionCurrent: boolean, collapsed: boolean): string {
  const layout = `group relative flex min-h-10 items-center gap-3 rounded-lg text-sm transition-colors ${collapsed ? 'justify-center px-0' : 'px-3'}`;
  if (active)
    return `${layout} bg-surface-2 text-text before:absolute before:top-2 before:bottom-2 before:left-0 before:w-0.5 before:rounded-full before:bg-ember`;
  if (sectionCurrent) return `${layout} text-text hover:bg-surface`;
  return `${layout} text-muted hover:bg-surface hover:text-text`;
}

/**
 * One destination. Only the most specific destination is the current page; its parent
 * is marked as the current section so a detail page keeps its place in the hierarchy.
 */
export function RailLink({ item, collapsed, onNavigate }: RailLinkProps) {
  const { pathname } = useLocation();
  const active = isWorkspacePath(item.to, pathname);
  const sectionCurrent = !active && containsWorkspacePath(item, pathname);
  return (
    <Link
      to={item.to}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      data-section-current={sectionCurrent ? 'true' : undefined}
      title={collapsed ? item.label : undefined}
      className={linkClass(active, sectionCurrent, collapsed)}
    >
      <RailIcon
        name={item.icon}
        className={active || sectionCurrent ? 'text-ember' : 'text-muted group-hover:text-text'}
      />
      <span className={collapsed ? 'sr-only' : 'min-w-0 leading-tight'}>{item.label}</span>
    </Link>
  );
}

/** A destination and, nested beneath it, the destinations it summarises. */
export function RailItem({ item, collapsed, onNavigate }: RailLinkProps) {
  const children = item.children ?? [];
  return (
    <li>
      <RailLink item={item} collapsed={collapsed} onNavigate={onNavigate} />
      {children.length > 0 && (
        <ul
          aria-label={`In ${item.label}`}
          className={`mt-0.5 flex flex-col gap-0.5 ${collapsed ? '' : 'ml-5 border-l border-line/70 pl-1.5'}`}
        >
          {children.map((child) => (
            <li key={child.to}>
              <RailLink item={child} collapsed={collapsed} onNavigate={onNavigate} />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
