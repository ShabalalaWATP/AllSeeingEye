import type { ReportVersion } from '@/lib/api/reports';
import { AiDisclosure } from './AiDisclosure';

/** The explicit no-evidence path writes a fixed notice without an assessment model call. */
export function ReportAiDisclosure({
  version,
  className,
}: {
  version: Pick<ReportVersion, 'findings'>;
  className?: string | undefined;
}) {
  if (version.findings.some((finding) => finding.rule === 'no_evidence')) {
    return (
      <p className={className ?? 'text-xs leading-5 text-muted'}>
        No AI assessment was generated. This version contains an application-written gap notice.
      </p>
    );
  }
  return <AiDisclosure className={className} />;
}
