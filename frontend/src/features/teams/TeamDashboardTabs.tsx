import { useRef, type KeyboardEvent } from 'react';

import { nextTabIndex, panelId, tabId, type DashboardTab } from './teamTabs';

/**
 * WAI-ARIA tabs with automatic activation: one tab stop (roving tabIndex), arrow keys
 * wrap, Home and End jump, and only the selected tab references the rendered panel.
 */
export function TeamDashboardTabs<Id extends string>({
  label,
  tabs,
  activeTab,
  onTabChange,
}: {
  label: string;
  tabs: readonly DashboardTab<Id>[];
  activeTab: Id;
  onTabChange: (tab: Id) => void;
}) {
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
            id={tabId(tab.id)}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={selected ? panelId(tab.id) : undefined}
            tabIndex={selected ? 0 : -1}
            onClick={() => onTabChange(tab.id)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={`min-h-12 shrink-0 border-b-2 px-3 text-left text-sm transition-colors ${
              selected
                ? 'border-ember text-text'
                : 'border-transparent text-muted hover:border-line hover:text-text'
            }`}
          >
            <span className="block font-medium">{tab.label}</span>
            <span className="mt-0.5 hidden text-2xs text-muted lg:block">{tab.detail}</span>
          </button>
        );
      })}
    </div>
  );
}
