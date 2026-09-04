import type { ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react';

export interface TableProps {
  caption: string;
  children: ReactNode;
}

/** A horizontally scrollable table with a visually hidden caption for screen readers. */
export function Table({ caption, children }: TableProps) {
  return (
    <div className="overflow-x-auto rounded-card border border-line bg-surface">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function Th({ className = '', children, ...rest }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={`border-b border-line px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted ${className}`}
      {...rest}
    >
      {children}
    </th>
  );
}

export function Td({ className = '', children, ...rest }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={`border-b border-line/60 px-3 py-2 align-top ${className}`} {...rest}>
      {children}
    </td>
  );
}
