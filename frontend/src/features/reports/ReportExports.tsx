import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchReportFile } from '@/lib/api/reportDocuments';
import type { ReportExportFormat } from '@/lib/api/reportDocuments';
import { fileNameFor } from '@/lib/download';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

export function ReportExports({
  id,
  version,
  title,
}: {
  id: string;
  version: number;
  title: string;
}) {
  const download = useAsyncAction(async (format: ReportExportFormat) => {
    const blob = await fetchReportFile(id, version, format);
    saveBinaryFile(fileNameFor(`${title}-v${String(version)}`, format), blob);
  });
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Document exports">
      <Button variant="secondary" busy={download.busy} onClick={() => void download.run('pdf')}>
        Download PDF
      </Button>
      <Button variant="secondary" busy={download.busy} onClick={() => void download.run('docx')}>
        Download DOCX
      </Button>
      {download.error === null ? null : <Alert tone="error">{describeError(download.error)}</Alert>}
    </div>
  );
}
