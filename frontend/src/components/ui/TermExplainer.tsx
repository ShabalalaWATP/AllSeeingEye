import { useId, useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

/**
 * A named button that opens an explanation beside it. It works by click, touch and keyboard,
 * never by hover alone; Escape or Close hides it and returns focus to the button.
 */
export function TermExplainer({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && open) {
      event.stopPropagation();
      close();
    }
  };
  return (
    // The wrapper only listens for Escape from the button or panel inside it.
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions
    <span className="inline-block" onKeyDown={onKeyDown}>
      <button
        ref={trigger}
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => (open ? close() : setOpen(true))}
        className="min-h-9 rounded-md px-1 text-xs text-ember underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-ember"
      >
        {label}
      </button>
      {open && (
        <section
          id={panelId}
          aria-label={label}
          className="mt-2 block max-w-prose rounded-md border border-line bg-surface p-3 text-left text-xs leading-5 text-text"
        >
          {children}
          <button
            type="button"
            onClick={close}
            className="mt-2 min-h-9 rounded-md border border-line px-3 text-xs text-text"
          >
            Close
          </button>
        </section>
      )}
    </span>
  );
}
