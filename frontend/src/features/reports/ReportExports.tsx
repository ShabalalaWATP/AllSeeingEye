import { useEffect, useId, useRef, useState } from 'react';

import { PdfLanguageNotice } from '@/components/reports/PdfLanguageNotice';
import { Alert } from '@/components/ui/Alert';
import { describeError } from '@/lib/api/errors';
import { fetchReportFile } from '@/lib/api/reportDocuments';
import type { ReportExportFormat } from '@/lib/api/reportDocuments';
import { fetchReportMarkdown } from '@/lib/api/reports';
import { fileNameFor, saveTextFile } from '@/lib/download';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

const formatLabels = {
  pdf: ['PDF', 'Fixed layout for reading and printing'],
  docx: ['Word (.docx)', 'Editable document with native headings and tables'],
  md: ['Markdown', 'Portable plain-text report with linked references'],
} as const;

export function ReportExports({
  id,
  version,
  title,
  preferred = 'pdf',
  language,
}: {
  id: string;
  version: number;
  title: string;
  preferred?: ReportExportFormat | 'md';
  language?: string | undefined;
}) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const closeMenu = (restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) trigger.current?.focus();
  };
  const download = useAsyncAction(async (format: ReportExportFormat | 'md') => {
    if (format === 'md') {
      const text = await fetchReportMarkdown(id, version);
      saveTextFile(fileNameFor(`${title}-v${String(version)}`, 'md'), text);
    } else {
      const blob = await fetchReportFile(id, version, format);
      saveBinaryFile(fileNameFor(`${title}-v${String(version)}`, format), blob);
    }
    closeMenu(true);
  });

  useEffect(() => {
    const container = root.current;
    if (!container) return;
    const dismissOnFocusOut = (event: FocusEvent) => {
      if (!container.contains(event.relatedTarget as Node | null)) setOpen(false);
    };
    container.addEventListener('focusout', dismissOnFocusOut);
    return () => container.removeEventListener('focusout', dismissOnFocusOut);
  }, []);

  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
    const dismiss = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', dismiss);
    return () => document.removeEventListener('mousedown', dismiss);
  }, [open]);

  const formats = [
    preferred,
    ...(['pdf', 'docx', 'md'] as const).filter((format) => format !== preferred),
  ];
  return (
    <div ref={root} className="relative" aria-label="Document exports">
      <button
        ref={trigger}
        type="button"
        className="inline-flex min-w-28 items-center justify-center gap-2 rounded-md bg-ember px-3 py-2 text-sm font-medium text-ground transition-colors hover:bg-ember/90 disabled:cursor-not-allowed disabled:opacity-50"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((current) => !current)}
      >
        <span aria-hidden="true">↓</span> Export
      </button>
      {open && (
        <div
          id={menuId}
          role="menu"
          tabIndex={-1}
          aria-label="Export report"
          className="absolute right-0 z-30 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-card border border-line bg-surface p-2 shadow-card"
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.preventDefault();
              event.stopPropagation();
              closeMenu(true);
              return;
            }
            if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const items = Array.from(
              event.currentTarget.querySelectorAll<HTMLElement>('[role="menuitem"]'),
            );
            const current = items.indexOf(document.activeElement as HTMLElement);
            const next =
              event.key === 'Home'
                ? 0
                : event.key === 'End'
                  ? items.length - 1
                  : event.key === 'ArrowDown'
                    ? (current + 1) % items.length
                    : (current - 1 + items.length) % items.length;
            items[next]?.focus();
          }}
        >
          <p className="px-2 pt-1 text-[11px] font-medium uppercase tracking-[0.16em] text-muted">
            Report version {version}
          </p>
          <div className="mt-1 divide-y divide-line">
            {formats.map((format) => {
              const [label, detail] = formatLabels[format];
              return (
                <button
                  key={format}
                  type="button"
                  role="menuitem"
                  aria-label={`Download ${format === 'docx' ? 'DOCX' : format === 'md' ? 'Markdown' : 'PDF'}`}
                  disabled={download.busy}
                  className="flex w-full items-start justify-between gap-4 rounded px-2 py-3 text-left transition-colors hover:bg-surface-2 disabled:opacity-50 motion-reduce:transition-none"
                  onClick={() => void download.run(format)}
                >
                  <span>
                    <span className="block text-sm font-medium text-text">{label}</span>
                    <span className="mt-0.5 block text-xs leading-5 text-muted">{detail}</span>
                  </span>
                  {format === preferred && (
                    <span className="rounded-full bg-ember/15 px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-ember">
                      Preferred
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <PdfLanguageNotice language={language} />
          {download.error === null ? null : (
            <Alert tone="error" className="mt-2">
              {describeError(download.error)}
            </Alert>
          )}
        </div>
      )}
    </div>
  );
}
