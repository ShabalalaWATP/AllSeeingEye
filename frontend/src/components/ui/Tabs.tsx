/**
 * The one tab strip (KAN-99), in two forms that look alike:
 * - Route tabs (`links`): the views of a workspace, each its own address. They are a
 *   labelled navigation of links, the current one marked `aria-current="page"`, because
 *   they change the page rather than a panel on it.
 * - Panel tabs (`tabs`): WAI-ARIA tabs with automatic activation that switch one panel in
 *   place. One tab stop (roving tabIndex), arrow keys wrap, Home and End jump, and only the
 *   selected tab references the rendered panel; give that panel `tabPanelProps`.
 */
import { useRef, type KeyboardEvent } from 'react';
import { NavLink } from 'react-router';

export interface TabLink {
  readonly to: string;
  readonly label: string;
}

export interface PanelTab<Id extends string> {
  readonly id: Id;
  readonly label: string;
  /** A short line under the label on wide screens. */
  readonly detail?: string | undefined;
}

interface RouteTabsProps {
  label: string;
  links: readonly TabLink[];
}

interface PanelTabsProps<Id extends string> {
  label: string;
  tabs: readonly PanelTab<Id>[];
  activeTab: Id;
  onTabChange: (tab: Id) => void;
  /** Prefixes the tab and panel ids; unique on the page. */
  idPrefix: string;
}

export type TabsProps<Id extends string> = RouteTabsProps | PanelTabsProps<Id>;

const TAB = 'border-b-2 text-sm transition-colors';
const CURRENT = 'border-ember text-text';
const OTHER = 'border-transparent text-muted hover:border-line hover:text-text';

export const tabId = (prefix: string, id: string) => `${prefix}-${id}-tab`;
export const panelId = (prefix: string, id: string) => `${prefix}-panel-${id}`;

/** The attributes for the panel the selected tab controls. */
export function tabPanelProps(prefix: string, id: string) {
  return { id: panelId(prefix, id), role: 'tabpanel', 'aria-labelledby': tabId(prefix, id) };
}

/** Next index for a tablist key press, or null when the key is not a tab navigation key. */
export function nextTabIndex(key: string, current: number, count: number): number | null {
  if (key === 'ArrowRight') return (current + 1) % count;
  if (key === 'ArrowLeft') return (current - 1 + count) % count;
  if (key === 'Home') return 0;
  if (key === 'End') return count - 1;
  return null;
}

export function Tabs<Id extends string>(props: TabsProps<Id>) {
  return 'links' in props ? <RouteTabs {...props} /> : <PanelTabs {...props} />;
}

/**
 * A tab that is the start of another tab's address matches only exactly; any other tab
 * also stays current on its detail pages, such as one research job under progress.
 */
function exactOnly(tab: TabLink, tabs: readonly TabLink[]): boolean {
  return tabs.some((other) => other !== tab && other.to.startsWith(`${tab.to}/`));
}

function RouteTabs({ label, links }: RouteTabsProps) {
  return (
    <nav aria-label={label} className="flex flex-wrap gap-x-5 gap-y-1 border-b border-line">
      {links.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={exactOnly(tab, links)}
          className={({ isActive }) => `${TAB} py-3 ${isActive ? CURRENT : OTHER}`}
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}

function PanelTabs<Id extends string>({
  label,
  tabs,
  activeTab,
  onTabChange,
  idPrefix,
}: PanelTabsProps<Id>) {
  const buttons = useRef(new Map<Id, HTMLButtonElement>());

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const next = nextTabIndex(event.key, index, tabs.length);
    const target = next === null ? undefined : tabs[next];
    if (target === undefined) return;
    event.preventDefault();
    onTabChange(target.id);
    buttons.current.get(target.id)?.focus();
  };

  return (
    <div
      role="tablist"
      aria-label={label}
      aria-orientation="horizontal"
      className="-mb-px flex gap-1 overflow-x-auto border-b border-line/70"
    >
      {tabs.map((tab, index) => {
        const selected = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            ref={(node) => {
              if (node === null) buttons.current.delete(tab.id);
              else buttons.current.set(tab.id, node);
            }}
            id={tabId(idPrefix, tab.id)}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={selected ? panelId(idPrefix, tab.id) : undefined}
            tabIndex={selected ? 0 : -1}
            onClick={() => onTabChange(tab.id)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={`${TAB} min-h-12 shrink-0 px-3 text-left ${selected ? CURRENT : OTHER}`}
          >
            <span className="block font-medium">{tab.label}</span>
            {tab.detail === undefined ? null : (
              <span className="mt-0.5 hidden text-2xs text-muted lg:block">{tab.detail}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
