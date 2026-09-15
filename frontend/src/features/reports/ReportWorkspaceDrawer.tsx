import { lazy, Suspense, useEffect, useRef } from 'react';

import { LoadingNote } from '@/components/ui/Alert';
import type { ReportSupportingWorkspaceProps } from './ReportSupportingWorkspace';

const ReportSupportingWorkspace = lazy(() => import('./ReportSupportingWorkspace'));

function reachable(node: HTMLElement, panel: HTMLElement): boolean {
  for (
    let current: HTMLElement | null = node;
    current && current !== panel;
    current = current.parentElement
  ) {
    if (current.hidden || current.inert || current.getAttribute('aria-hidden') === 'true')
      return false;
    const style = getComputedStyle(current);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    if (current instanceof HTMLDetailsElement && !current.open) {
      const summary = current.querySelector(':scope > summary');
      if (!summary?.contains(node)) return false;
    }
  }
  return true;
}

export function ReportWorkspaceDrawer({
  open,
  onClose,
  workspace,
}: {
  open: boolean;
  onClose: () => void;
  workspace: ReportSupportingWorkspaceProps;
}) {
  const close = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    close.current?.focus();
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !panel.current) return;
      const container = panel.current;
      const focusable = Array.from(
        container.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((node) => reachable(node, container));
      const first = focusable[0];
      const last = focusable.at(-1);
      if (!first || !last) return;
      if (!container.contains(document.activeElement)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', keyboard);
    return () => {
      document.removeEventListener('keydown', keyboard);
      previous?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/65 backdrop-blur-[2px]">
      <button
        type="button"
        aria-label="Close sources and methods"
        className="absolute inset-0 h-full w-full cursor-default"
        onClick={onClose}
      />
      <aside
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="supporting-workspace-title"
        className="absolute inset-y-2 right-2 flex w-[min(58rem,calc(100vw-1rem))] flex-col overflow-hidden rounded-card border border-line bg-surface shadow-card sm:inset-y-4 sm:right-4 sm:w-[min(58rem,calc(100vw-2rem))]"
      >
        <header className="flex items-start justify-between gap-6 border-b border-line px-5 py-4 sm:px-7">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-ember">
              Supporting workspace
            </p>
            <h2 id="supporting-workspace-title" className="mt-1 text-lg font-semibold">
              Sources and methods
            </h2>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-muted">
              Inspect retained evidence, collection coverage and analytical review for this exact
              report version.
            </p>
          </div>
          <button
            ref={close}
            type="button"
            className="rounded px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-text motion-reduce:transition-none"
            onClick={onClose}
          >
            Close
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 sm:px-7">
          <Suspense fallback={<LoadingNote label="Loading supporting material" />}>
            <ReportSupportingWorkspace {...workspace} />
          </Suspense>
        </div>
      </aside>
    </div>
  );
}
