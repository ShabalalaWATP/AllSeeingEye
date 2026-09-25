import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router';

import { Button } from '@/components/ui/Button';
import { SHORTCUT_GROUPS } from '@/lib/keyboardShortcuts';
import type { ShortcutEntry } from '@/lib/keyboardShortcuts';
import { usePreferencesStore } from '@/stores/preferences';

/** The shortcut list, opened with ? or from Settings. Mounted once in the top bar. */
export function ShortcutHelp() {
  const open = usePreferencesStore((state) => state.shortcutHelpOpen);
  return open ? <ShortcutHelpDialog /> : null;
}

function Keys({ keys }: { keys: readonly string[] }) {
  return (
    <span className="flex flex-wrap items-center gap-1 text-xs text-muted">
      {keys.map((key, index) => (
        <span key={key} className="inline-flex items-center gap-1">
          {index > 0 && <span>or</span>}
          <kbd className="min-w-6 rounded border border-line bg-surface-2 px-1.5 py-0.5 text-center font-mono text-xs text-text">
            {key}
          </kbd>
        </span>
      ))}
    </span>
  );
}

function ShortcutRow({ entry, singleKeyOn }: { entry: ShortcutEntry; singleKeyOn: boolean }) {
  const off = entry.singleKey === true && !singleKeyOn;
  return (
    <div className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)] items-baseline gap-3 py-2">
      <dt>
        <Keys keys={entry.keys} />
      </dt>
      <dd className={`text-sm ${off ? 'text-muted' : 'text-text'}`}>
        {entry.action}
        {off && <span className="ml-2 font-mono text-xs text-muted uppercase">Off</span>}
      </dd>
    </div>
  );
}

function ShortcutHelpDialog() {
  const close = usePreferencesStore((state) => state.closeShortcutHelp);
  const singleKeyOn = usePreferencesStore((state) => state.singleKeyShortcuts);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const opener = document.activeElement;
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => {
      dialog?.close();
      // Let the native close settle before returning focus to whatever opened the help.
      queueMicrotask(() => {
        if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
      });
    };
  }, []);

  return createPortal(
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className="fixed top-[8vh] left-1/2 m-0 max-h-[84vh] w-[min(36rem,calc(100vw-2rem))] -translate-x-1/2 overflow-y-auto rounded-xl border border-line bg-ground p-0 text-text backdrop:bg-black/65"
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
    >
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2">
        <h2 id={titleId} className="text-base font-semibold">
          Keyboard shortcuts
        </h2>
        <Button variant="ghost" className="min-h-11" onClick={close}>
          Close
        </Button>
      </div>
      <div className="space-y-5 px-4 py-4">
        {!singleKeyOn && (
          <p className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-muted">
            Single-key shortcuts are off, so only shortcuts with a modifier or a focused control
            work. You can turn them back on in{' '}
            <Link
              to="/settings?section=keyboard"
              onClick={close}
              className="text-ember underline underline-offset-2"
            >
              keyboard settings
            </Link>
            .
          </p>
        )}
        {SHORTCUT_GROUPS.map((group) => (
          <section key={group.title} aria-label={group.title}>
            <h3 className="font-mono text-xs tracking-widest text-muted uppercase">
              {group.title}
            </h3>
            <dl className="mt-1 divide-y divide-line/60">
              {group.entries.map((entry) => (
                <ShortcutRow
                  key={`${entry.keys.join('+')}:${entry.action}`}
                  entry={entry}
                  singleKeyOn={singleKeyOn}
                />
              ))}
            </dl>
          </section>
        ))}
      </div>
    </dialog>,
    document.body,
  );
}
