/**
 * Labelled form controls. Each control gets a generated id, its label is bound
 * with htmlFor, and hint and error text are linked through aria-describedby so
 * assistive technology reads them with the field.
 */
import { useId } from 'react';
import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react';

interface FieldFrameProps {
  label: string;
  /** Keeps the label for assistive technology only (dense tables). */
  labelHidden?: boolean | undefined;
  hint?: string | undefined;
  error?: string | undefined;
}

const controlClass =
  'w-full rounded-md border border-line bg-ground px-3 py-2 text-sm text-text ' +
  'placeholder:text-muted/70 aria-invalid:border-critical disabled:opacity-50';

function useFieldIds(hint: string | undefined, error: string | undefined) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint === undefined ? null : hintId, error === undefined ? null : errorId]
    .filter((value): value is string => value !== null)
    .join(' ');
  return { id, hintId, errorId, describedBy: describedBy === '' ? undefined : describedBy };
}

function FieldFrame({
  id,
  label,
  labelHidden = false,
  hint,
  hintId,
  error,
  errorId,
  children,
}: FieldFrameProps & { id: string; hintId: string; errorId: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className={labelHidden ? 'sr-only' : 'text-sm font-medium text-text'}>
        {label}
      </label>
      {hint === undefined ? null : (
        <p id={hintId} className="text-xs text-muted">
          {hint}
        </p>
      )}
      {children}
      {error === undefined ? null : (
        <p id={errorId} role="alert" className="text-sm text-critical">
          {error}
        </p>
      )}
    </div>
  );
}

export interface TextFieldProps
  extends FieldFrameProps, Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'aria-describedby'> {}

export function TextField({
  label,
  labelHidden,
  hint,
  error,
  className = '',
  ...rest
}: TextFieldProps) {
  const ids = useFieldIds(hint, error);
  return (
    <FieldFrame label={label} labelHidden={labelHidden} hint={hint} error={error} {...ids}>
      <input
        id={ids.id}
        className={`${controlClass} ${className}`}
        aria-invalid={error === undefined ? undefined : true}
        aria-describedby={ids.describedBy}
        {...rest}
      />
    </FieldFrame>
  );
}

export interface TextAreaFieldProps
  extends FieldFrameProps, Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id' | 'aria-describedby'> {}

export function TextAreaField({
  label,
  labelHidden,
  hint,
  error,
  className = '',
  ...rest
}: TextAreaFieldProps) {
  const ids = useFieldIds(hint, error);
  return (
    <FieldFrame label={label} labelHidden={labelHidden} hint={hint} error={error} {...ids}>
      <textarea
        id={ids.id}
        className={`${controlClass} min-h-24 ${className}`}
        aria-invalid={error === undefined ? undefined : true}
        aria-describedby={ids.describedBy}
        {...rest}
      />
    </FieldFrame>
  );
}

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectFieldProps
  extends FieldFrameProps, Omit<SelectHTMLAttributes<HTMLSelectElement>, 'id' | 'aria-describedby'> {
  options: readonly SelectOption[];
}

export function SelectField({
  label,
  labelHidden,
  hint,
  error,
  options,
  className = '',
  ...rest
}: SelectFieldProps) {
  const ids = useFieldIds(hint, error);
  return (
    <FieldFrame label={label} labelHidden={labelHidden} hint={hint} error={error} {...ids}>
      <select
        id={ids.id}
        className={`${controlClass} ${className}`}
        aria-invalid={error === undefined ? undefined : true}
        aria-describedby={ids.describedBy}
        {...rest}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldFrame>
  );
}
