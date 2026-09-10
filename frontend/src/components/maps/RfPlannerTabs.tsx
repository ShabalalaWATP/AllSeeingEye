import { Component, createRef, useId, useRef } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

interface PanelProps {
  id: string;
  view: 'configure' | 'results';
  labelledBy: string;
  focusTab: () => void;
  children: ReactNode;
}

/** Capture focus before React removes a completed form or result action. */
class PlannerPanel extends Component<PanelProps, Record<string, never>, boolean> {
  private readonly panel = createRef<HTMLDivElement>();

  override getSnapshotBeforeUpdate(previous: PanelProps) {
    return (
      previous.view !== this.props.view && !!this.panel.current?.contains(document.activeElement)
    );
  }

  override componentDidUpdate(
    _previous: PanelProps,
    _state: Record<string, never>,
    restoreFocus: boolean,
  ) {
    if (restoreFocus) this.props.focusTab();
  }

  override render() {
    return (
      <div
        ref={this.panel}
        id={this.props.id}
        role="tabpanel"
        aria-labelledby={this.props.labelledBy}
        tabIndex={-1}
      >
        {this.props.children}
      </div>
    );
  }
}

export function RfPlannerTabs({
  view,
  onChange,
  hasResults,
  children,
}: {
  view: 'configure' | 'results';
  onChange: (view: 'configure' | 'results') => void;
  hasResults: boolean;
  children: ReactNode;
}) {
  const id = useId();
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const keys = ['configure', 'results'] as const;
  const keyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = !hasResults || event.key === 'Home' ? 0 : event.key === 'End' ? 1 : 1 - index;
    onChange(next === 0 ? 'configure' : 'results');
    tabs.current[next]?.focus();
  };
  return (
    <>
      <div className="rf-planner-tabs" role="tablist" aria-label="Radio planner sections">
        {keys.map((key, index) => (
          <button
            key={key}
            ref={(node) => {
              tabs.current[index] = node;
            }}
            type="button"
            role="tab"
            id={`${id}-${key}`}
            aria-controls={`${id}-panel`}
            aria-selected={view === key}
            disabled={key === 'results' && !hasResults}
            tabIndex={view === key ? 0 : -1}
            onClick={() => onChange(key)}
            onKeyDown={(event) => keyDown(event, index)}
          >
            <span className="rf-tab-number" aria-hidden="true">
              0{index + 1}
            </span>
            {key === 'configure' ? 'Configure' : 'Results'}
            {key === 'results' && hasResults && (
              <span className="rf-result-dot" aria-hidden="true" />
            )}
          </button>
        ))}
      </div>
      <PlannerPanel
        id={`${id}-panel`}
        view={view}
        labelledBy={`${id}-${view}`}
        focusTab={() => tabs.current[view === 'configure' ? 0 : 1]?.focus()}
      >
        {children}
      </PlannerPanel>
    </>
  );
}
