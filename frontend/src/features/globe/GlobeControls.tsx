import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';

const COMPACT_QUERY = '(width < 1024px)';
const readCompact = () =>
  typeof window.matchMedia === 'function' && window.matchMedia(COMPACT_QUERY).matches;
function subscribeCompact(onChange: () => void) {
  if (typeof window.matchMedia !== 'function') return () => undefined;
  const media = window.matchMedia(COMPACT_QUERY);
  media.addEventListener('change', onChange);
  return () => media.removeEventListener('change', onChange);
}

/** Desktop keeps its context column; smaller screens give the map the full canvas. */
export function GlobeControls({ children }: { children: ReactNode }) {
  const compact = useSyncExternalStore(subscribeCompact, readCompact, () => false);
  return compact ? (
    <CompactControls>{children}</CompactControls>
  ) : (
    <div className="absolute top-16 bottom-3 left-3 z-10 flex w-52 flex-col gap-2 overflow-y-auto">
      {children}
    </div>
  );
}

function CompactControls({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(true)}
        className="absolute top-3 right-3 z-10 min-h-11 rounded-md border border-line bg-surface/95 px-3 text-sm font-medium text-text backdrop-blur hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember"
      >
        Map controls
      </button>
      {open && <ControlsSheet onClose={() => setOpen(false)}>{children}</ControlsSheet>}
    </>
  );
}

/** Native modal focus and inertness stop accidental map gestures behind the sheet. */
function ControlsSheet({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => {
      dialog?.close();
      queueMicrotask(() => {
        if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
      });
    };
  }, []);

  return createPortal(
    <dialog
      ref={dialogRef}
      aria-label="Map controls"
      className="fixed inset-x-3 top-auto bottom-4 mx-auto my-0 max-h-[calc(100dvh-2rem)] w-full max-w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-xl border border-line bg-ground p-0 text-text open:flex backdrop:bg-black/60 sm:max-w-sm"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-line px-3 py-1.5">
        <h2 className="text-sm font-semibold">Map controls</h2>
        <button
          type="button"
          onClick={onClose}
          className="min-h-11 rounded-md px-3 text-sm text-ember hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember"
        >
          Close controls
        </button>
      </div>
      <div className="flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain p-3">
        {children}
      </div>
    </dialog>,
    document.body,
  );
}
