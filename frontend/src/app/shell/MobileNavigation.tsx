import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useLocation } from 'react-router';

import { Button } from '@/components/ui/Button';

import { LeftRail } from './LeftRail';
import { TopBar } from './TopBar';

/** Local state is discarded when desktop or operations-room mode replaces this header. */
export function MobileHeader() {
  const { key } = useLocation();
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  return (
    <>
      <TopBar onOpenNavigation={() => setOpenedAt(key)} />
      {openedAt === key && <MobileNavigation onClose={() => setOpenedAt(null)} />}
    </>
  );
}

/** Native modal semantics keep focus inside and the map inert until dismissed. */
export function MobileNavigation({ onClose }: { onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => {
      dialog?.close();
      // Allow native modal close/focus restoration to settle before restoring it explicitly.
      queueMicrotask(() => {
        if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
      });
    };
  }, []);

  return createPortal(
    <dialog
      ref={dialogRef}
      aria-label="Navigation"
      className="fixed inset-y-0 left-0 m-0 h-dvh max-h-none w-72 max-w-[calc(100vw-2rem)] border-r border-line bg-ground p-0 text-text backdrop:bg-black/65"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="flex h-full flex-col">
        <div className="flex shrink-0 items-center justify-between border-b border-line px-4 py-2">
          <span className="font-mono text-xs uppercase tracking-widest text-muted">Navigation</span>
          <Button variant="ghost" className="min-h-11" onClick={onClose}>
            Close navigation
          </Button>
        </div>
        <LeftRail mobile onNavigate={onClose} />
      </div>
    </dialog>,
    document.body,
  );
}
