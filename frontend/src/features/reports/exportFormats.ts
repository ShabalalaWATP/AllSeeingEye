import type { ReportExportFormat } from '@/lib/api/reportDocuments';

export type ExportChoice = ReportExportFormat | 'md';

export interface ExportDescription {
  label: string;
  short: string;
  purpose: string;
  detail: string;
}

/**
 * What each export is for, in the reader's words. The descriptions state only what
 * the renderers actually produce; nothing here promises verification or fidelity the
 * exports do not have.
 */
export const EXPORT_FORMATS: Record<ExportChoice, ExportDescription> = {
  pdf: {
    label: 'PDF',
    short: 'PDF',
    purpose: 'Share or print',
    detail:
      'Fixed A4 layout with a cover block, running heads, page numbers and numbered endnotes.',
  },
  docx: {
    label: 'Word (.docx)',
    short: 'DOCX',
    purpose: 'Edit or comment',
    detail: 'Native Word headings, tables and bookmarks, so the document stays editable.',
  },
  md: {
    label: 'Markdown',
    short: 'Markdown',
    purpose: 'Archive or diff',
    detail: 'Plain text with the full evidence annex. Figures arrive as local images inside a ZIP.',
  },
};

/**
 * A caveat to show against one format, or null when it carries none. Language support
 * is the only per-format limitation the API reports; it is stated exactly as it is.
 */
export function exportCaveat(
  format: ExportChoice,
  options: { pdfLanguageUnsupported: boolean; languageLabel: string | null },
): string | null {
  if (format !== 'pdf' || !options.pdfLanguageUnsupported) return null;
  const language = options.languageLabel ?? 'this language';
  return `PDF cannot draw ${language} text correctly here and replaces unsupported characters with code labels. Use DOCX or Markdown to keep the original text.`;
}
