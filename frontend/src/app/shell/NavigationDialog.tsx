import { useEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@/components/ui/Button';

/** Native modal semantics keep focus inside and the map inert until dismissed. */
export function NavigationDialog({
  onClose,
  children,
  label = 'Navigation',
}: {
  onClose: () => void;
  children: ReactNode;
  label?: string;
}) {
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
      aria-label={label}
      className="fixed inset-y-0 left-0 m-0 h-dvh max-h-none w-72 max-w-[calc(100vw-2rem)] border-r border-line bg-ground p-0 text-text backdrop:bg-black/65"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="flex h-full flex-col">
        <div className="flex shrink-0 items-center justify-between border-b border-line px-4 py-2">
          <span className="font-mono text-xs uppercase tracking-widest text-muted">{label}</span>
          <Button variant="ghost" className="min-h-11" onClick={onClose}>
            Close navigation
          </Button>
        </div>
        {children}
      </div>
    </dialog>,
    document.body,
  );
}
