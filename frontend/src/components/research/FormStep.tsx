/**
 * The building blocks of a form read top to bottom: a numbered step with a heading and a
 * one-line lead, and a boxed on/off choice. Research and subscriptions share them so the
 * two forms feel like one product.
 */
import type { ReactNode } from 'react';

export function Step({
  number,
  title,
  lead,
  id,
  children,
}: {
  number: number;
  title: string;
  lead?: string;
  id?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id ?? title}-heading`} className="grid gap-4">
      <header className="flex items-baseline gap-3">
        <span
          aria-hidden="true"
          className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-ember/15 font-mono text-[11px] text-ember"
        >
          {number}
        </span>
        <div>
          <h3 id={`${id ?? title}-heading`} className="text-base font-semibold">
            {title}
          </h3>
          {lead && <p className="mt-1 text-xs leading-5 text-muted">{lead}</p>}
        </div>
      </header>
      <div className="grid gap-4 pl-10">{children}</div>
    </section>
  );
}

export function Toggle({
  checked,
  onChange,
  title,
  detail,
  disabled = false,
  children,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  title: string;
  detail: string;
  disabled?: boolean;
  children?: ReactNode;
}) {
  return (
    <label className="flex items-start gap-3 rounded-xl border border-line bg-ground p-4 text-sm has-checked:border-ember/40">
      <input
        type="checkbox"
        className="mt-1 h-4 w-4 accent-ember"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>
        {title}
        <span className="mt-1 block text-xs leading-5 text-muted">{detail}</span>
        {children}
      </span>
    </label>
  );
}
