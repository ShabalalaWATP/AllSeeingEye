import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router';

import { selectIsAdmin, useAuthStore } from '@/stores/auth';
import { useShellStore } from '@/stores/shell';

import { commandTargets, matchTargets } from './commandTargets';

/** One keyboard route to every page, tracker, map layer and source family. */
export function CommandPalette() {
  const close = useShellStore((state) => state.closePalette);
  const navigate = useNavigate();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const optionId = useId();
  const [query, setQuery] = useState('');
  const [index, setIndex] = useState(0);
  const isAdmin = useAuthStore(selectIsAdmin);
  const targets = useMemo(() => commandTargets({ admin: isAdmin }), [isAdmin]);
  const matches = useMemo(() => matchTargets(targets, query), [targets, query]);
  const active = matches[Math.min(index, matches.length - 1)];

  useEffect(() => {
    const opener = document.activeElement;
    const dialog = dialogRef.current;
    dialog?.showModal();
    inputRef.current?.focus();
    return () => {
      dialog?.close();
      queueMicrotask(() => {
        if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
      });
    };
  }, []);

  const go = (to: string) => {
    close();
    void navigate(to);
  };

  return createPortal(
    <dialog
      ref={dialogRef}
      aria-label="Find anything"
      className="fixed top-[8vh] left-1/2 m-0 w-[min(34rem,calc(100vw-1.5rem))] -translate-x-1/2 rounded-xl border border-line bg-ground p-0 text-text backdrop:bg-black/65"
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
    >
      <div className="flex max-h-[min(70vh,32rem)] flex-col">
        <label className="border-b border-line px-3 py-2">
          <span className="sr-only">Search pages, trackers, map layers and sources</span>
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={active ? `${optionId}-${active.id}` : undefined}
            value={query}
            placeholder="Search pages, trackers, map layers and sources"
            onChange={(event) => {
              setQuery(event.target.value.slice(0, 120));
              setIndex(0);
            }}
            onKeyDown={(event) => {
              if (event.key === 'ArrowDown') {
                event.preventDefault();
                setIndex((current) => Math.min(current + 1, matches.length - 1));
              } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                setIndex((current) => Math.max(current - 1, 0));
              } else if (event.key === 'Enter' && active) {
                event.preventDefault();
                go(active.to);
              }
            }}
            className="min-h-11 w-full bg-transparent text-sm text-text outline-none placeholder:text-muted"
          />
        </label>
        <div
          id={listId}
          role="listbox"
          aria-label="Results"
          className="min-h-0 flex-1 overflow-y-auto p-1"
        >
          {matches.map((target, position) => (
            <button
              key={target.id}
              id={`${optionId}-${target.id}`}
              type="button"
              role="option"
              aria-selected={active?.id === target.id}
              tabIndex={-1}
              onClick={() => {
                go(target.to);
              }}
              onMouseEnter={() => {
                setIndex(position);
              }}
              className={`flex w-full flex-col gap-0.5 rounded-lg px-3 py-2 text-left ${
                active?.id === target.id ? 'bg-surface-2' : 'hover:bg-surface'
              }`}
            >
              <span className="flex items-baseline gap-2">
                <span className="min-w-0 truncate text-sm">{target.label}</span>
                <span className="shrink-0 font-mono text-[10px] tracking-widest text-muted uppercase">
                  {target.group}
                </span>
              </span>
              <span className="text-[11px] leading-relaxed text-muted">{target.description}</span>
            </button>
          ))}
          {matches.length === 0 && (
            <p className="px-3 py-6 text-center text-sm text-muted">Nothing matches that.</p>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 border-t border-line px-3 py-2">
          <p className="text-[11px] text-muted">Arrow keys to move, Enter to open, Esc to close.</p>
          <button
            type="button"
            onClick={close}
            className="min-h-11 rounded-md px-3 text-sm text-muted hover:text-text focus-visible:outline-2 focus-visible:outline-ember"
          >
            Close search
          </button>
        </div>
      </div>
    </dialog>,
    document.body,
  );
}
