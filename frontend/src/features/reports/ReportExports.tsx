import { Alert } from '@/components/ui/Alert';
import { PdfLanguageNotice } from '@/components/reports/PdfLanguageNotice';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchReportFile } from '@/lib/api/reportDocuments';
import type { ReportExportFormat } from '@/lib/api/reportDocuments';
import { fetchReportMarkdown } from '@/lib/api/reports';
import { saveTextFile } from '@/lib/download';
import { fileNameFor } from '@/lib/download';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

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
  const download = useAsyncAction(async (format: ReportExportFormat | 'md') => {
    if (format === 'md') {
      const text = await fetchReportMarkdown(id, version);
      saveTextFile(fileNameFor(`${title}-v${String(version)}`, 'md'), text);
      return;
    }
    const blob = await fetchReportFile(id, version, format);
    saveBinaryFile(fileNameFor(`${title}-v${String(version)}`, format), blob);
  });
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Document exports">
      <PdfLanguageNotice language={language} />
      {[
        preferred,
        ...(['pdf', 'docx', 'md'] as const).filter((format) => format !== preferred),
      ].map((format) => (
        <Button
          key={format}
          variant={format === preferred ? 'primary' : 'secondary'}
          busy={download.busy}
          onClick={() => void download.run(format)}
        >
          Download {format === 'md' ? 'Markdown' : format.toUpperCase()}
        </Button>
      ))}
      <span className="w-full text-xs text-muted">
        Preferred format: {preferred === 'md' ? 'Markdown' : preferred.toUpperCase()}. Change this
        in your profile.
      </span>
      {download.error === null ? null : <Alert tone="error">{describeError(download.error)}</Alert>}
    </div>
  );
}
