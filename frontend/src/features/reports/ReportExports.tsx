import { useEffect, useId, useRef, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchReportFile, fetchReportStix, type StixTlp } from '@/lib/api/reportDocuments';
import { fetchReportMarkdown } from '@/lib/api/reports';
import type { ReportStatus } from '@/lib/api/reports';
import { fileNameFor, saveTextFile } from '@/lib/download';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useLanguageCatalogue } from '@/lib/hooks/useLanguageCatalogue';

import { EXPORT_FORMATS, exportCaveat, type ExportChoice } from './exportFormats';
import { ExportMenuItem } from './ExportMenuItem';

const FALLBACK_LANGUAGES: Record<string, string> = {
  ar: 'Arabic',
  fa: 'Persian',
  'zh-CN': 'Chinese (China)',
  'zh-TW': 'Chinese (Taiwan)',
};

const STATUS_NOTE: Record<ReportStatus, string> = {
  ready: 'Every export carries the same automated-check status as this page.',
  needs_review: 'Every export repeats the review notice shown on this page.',
  failed: 'Every export states that this version is not a completed assessment.',
};

export function ReportExports({
  id,
  version,
  title,
  preferred = 'pdf',
  language,
  status,
}: {
  id: string;
  version: number;
  title: string;
  preferred?: ExportChoice;
  language?: string | undefined;
  status?: ReportStatus | undefined;
}) {
  const [open, setOpen] = useState(false);
  const [tlp, setTlp] = useState<StixTlp | ''>('');
  const [preparing, setPreparing] = useState<ExportChoice | null>(null);
  const menuId = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const catalogue = useLanguageCatalogue();
  const capability = catalogue.data?.languages.find((entry) => entry.code === language);
  const languageLabel = capability?.label ?? FALLBACK_LANGUAGES[language ?? ''] ?? null;
  const pdfLanguageUnsupported = capability
    ? !capability.pdf_supported
    : Boolean(FALLBACK_LANGUAGES[language ?? '']);
  const closeMenu = (restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) trigger.current?.focus();
  };
  const download = useAsyncAction(async (format: ExportChoice) => {
    setPreparing(format);
    try {
      await saveExport(format);
    } finally {
      // Done either way: any failure shows beside the trigger. Focus returns to the trigger
      // only if the reader has not moved it elsewhere meanwhile.
      setPreparing(null);
      const focus = document.activeElement;
      closeMenu(
        focus === null || focus === document.body || root.current?.contains(focus) === true,
      );
    }
  });
  async function saveExport(format: ExportChoice) {
    if (format === 'stix') {
      if (!tlp) return;
      const blob = await fetchReportStix(id, version, tlp);
      saveBinaryFile(fileNameFor(`${title}-v${String(version)}`, 'stix.json'), blob);
    } else if (format === 'md') {
      const file = await fetchReportMarkdown(id, version);
      const fallback = fileNameFor(
        `${title}-v${String(version)}`,
        file.blob.type === 'application/zip' ? 'zip' : 'md',
      );
      if (file.blob.type === 'application/zip') {
        saveBinaryFile(file.filename ?? fallback, file.blob);
      } else {
        saveTextFile(file.filename ?? fallback, await file.blob.text());
      }
    } else {
      const blob = await fetchReportFile(id, version, format);
      saveBinaryFile(fileNameFor(`${title}-v${String(version)}`, format), blob);
    }
  }

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

  const formats: ExportChoice[] = [
    preferred,
    ...(['pdf', 'docx', 'md', 'stix'] as const).filter((format) => format !== preferred),
  ];
  return (
    <div ref={root} role="group" className="relative" aria-label="Document exports">
      <Button
        ref={trigger}
        className="min-w-28 motion-reduce:transition-none"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        busy={download.busy}
        busyLabel={`Preparing ${EXPORT_FORMATS[preparing ?? preferred].short}…`}
        onClick={() => setOpen((current) => !current)}
      >
        <span aria-hidden="true">↓</span> Export
      </Button>
      {open && (
        <div
          id={menuId}
          role="menu"
          tabIndex={-1}
          aria-label="Export report"
          className="absolute right-0 z-30 mt-2 w-[min(24rem,calc(100vw-2rem))] rounded-card border border-line bg-surface p-2 shadow-card"
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
          <div className="px-2 pb-2 pt-1">
            <p className="text-2xs font-medium uppercase tracking-[0.16em] text-muted">
              Report version {version}
            </p>
            <p className="mt-1 text-xs leading-5 text-muted">
              {status ? STATUS_NOTE[status] : 'Every export carries this version’s provenance.'}
            </p>
          </div>
          <div className="divide-y divide-line border-t border-line">
            <label className="block p-2 text-xs">
              STIX sharing marking
              <select
                aria-label="STIX sharing marking"
                value={tlp}
                onKeyDown={(event) => event.stopPropagation()}
                onChange={(event) => setTlp(event.target.value as StixTlp | '')}
              >
                <option value="">Choose a marking</option>
                <option value="green">TLP:GREEN</option>
                <option value="amber">TLP:AMBER</option>
                <option value="red">TLP:RED</option>
              </select>
            </label>
            {formats.map((format) => (
              <ExportMenuItem
                key={format}
                format={format}
                description={EXPORT_FORMATS[format]}
                preferred={format === preferred}
                busy={download.busy || (format === 'stix' && !tlp)}
                caveat={exportCaveat(format, { pdfLanguageUnsupported, languageLabel })}
                onSelect={() => void download.run(format)}
              />
            ))}
          </div>
        </div>
      )}
      {/* Beside the trigger, so a failure outlives the menu closing. */}
      {download.error === null ? null : (
        <Alert tone="error" className="mt-2 max-w-xs">
          {describeError(download.error)}
        </Alert>
      )}
    </div>
  );
}
