import { useState } from 'react';

export interface NumberFieldOptions {
  min: number;
  max: number;
  /** Round to whole numbers. */
  integer?: boolean;
}

export interface NumberField {
  /** The last accepted number, always within range. */
  value: number;
  /** Exactly what the reader has typed, so the field can be cleared and retyped. */
  text: string;
  /** Record typed text. A readable number updates `value` straight away, clamped. */
  type: (text: string) => void;
  /** Settle the text on the accepted value, for example on blur. */
  commit: () => void;
  /** Replace the value from elsewhere, such as a preset. */
  set: (value: number) => void;
}

function bounded(value: number, { min, max, integer = false }: NumberFieldOptions): number {
  const rounded = integer ? Math.round(value) : value;
  return Math.min(max, Math.max(min, rounded));
}

/**
 * A numeric input that never fights the keyboard. The typed string is kept as is, while
 * the value used elsewhere stays the last readable number within range. Blank or
 * unreadable text keeps that value and is replaced by it on commit.
 */
export function useNumberField(initial: number, options: NumberFieldOptions): NumberField {
  const [value, setValue] = useState(() => bounded(initial, options));
  const [text, setText] = useState(() => String(bounded(initial, options)));
  return {
    value,
    text,
    type: (next) => {
      setText(next);
      const parsed = Number(next);
      if (next.trim() !== '' && Number.isFinite(parsed)) setValue(bounded(parsed, options));
    },
    commit: () => setText(String(value)),
    set: (next) => {
      const settled = bounded(next, options);
      setValue(settled);
      setText(String(settled));
    },
  };
}
