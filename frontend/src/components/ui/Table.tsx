import type { ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react';

export interface TableProps {
  caption: string;
  children: ReactNode;
  /** Keeps column headings visible while a long table scrolls inside its own frame. */
  stickyHeader?: boolean | undefined;
  className?: string | undefined;
}

const STICKY =
  'max-h-[min(70vh,48rem)] overflow-y-auto [&_thead_th]:sticky [&_thead_th]:top-0 [&_thead_th]:z-[1] [&_thead_th]:bg-surface';

/** A horizontally scrollable table with a visually hidden caption for screen readers. */
export function Table({ caption, children, stickyHeader = false, className = '' }: TableProps) {
  return (
    <div
      className={`overflow-x-auto rounded-card border border-line bg-surface ${stickyHeader ? STICKY : ''} ${className}`}
    >
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
