import { Table, Td, Th } from '@/components/ui/Table';
import type { QualityJobGroup, QualityVersionGroup } from '@/lib/api/researchQuality';

import { formatCount, receiptText, usageText } from './qualityPresentation';

function Count({ value }: { value: number }) {
  return <Td className="text-right font-mono text-xs">{formatCount(value)}</Td>;
}

function GroupHeader({ label, overall }: { label: string; overall: boolean }) {
  return (
    <Th scope="row" className={`text-left text-sm ${overall ? 'font-semibold' : 'font-normal'}`}>
      {label}
    </Th>
  );
}

/** Each row's denominator is its own version count; receipts and usage name theirs. */
export function VersionTable({
  caption,
  overall,
  groups,
}: {
  caption: string;
  overall: QualityVersionGroup;
  groups: QualityVersionGroup[];
}) {
  return (
    <Table caption={caption}>
      <thead>
        <tr>
          <Th>Group</Th>
          <Th className="text-right">Versions</Th>
          <Th className="text-right">Ready</Th>
          <Th className="text-right">Needs review</Th>
          <Th className="text-right">Failed</Th>
          <Th>Empty or unavailable receipts</Th>
          <Th>Model usage</Th>
        </tr>
      </thead>
      <tbody>
        {[overall, ...groups].map((group, index) => (
          <tr key={`${index === 0 ? 'overall' : 'group'}-${group.key}`}>
            <GroupHeader label={group.label} overall={index === 0} />
            <Count value={group.versions} />
            <Count value={group.ready} />
            <Count value={group.needs_review} />
            <Count value={group.failed} />
            <Td className="text-xs text-muted">{receiptText(group)}</Td>
            <Td className="min-w-48 text-xs text-muted">{usageText(group)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

/** Job statuses are a separate population; failed jobs are split by whether a version saved. */
export function JobTable({
  caption,
  overall,
  groups,
}: {
  caption: string;
  overall: QualityJobGroup;
  groups: QualityJobGroup[];
}) {
  return (
    <Table caption={caption}>
      <thead>
        <tr>
          <Th>Group</Th>
          <Th className="text-right">Jobs</Th>
          <Th className="text-right">Queued</Th>
          <Th className="text-right">Running</Th>
          <Th className="text-right">Paused</Th>
          <Th className="text-right">Completed</Th>
          <Th className="text-right">Needs review</Th>
          <Th className="text-right">Failed, no version saved</Th>
          <Th className="text-right">Failed, version saved</Th>
        </tr>
      </thead>
      <tbody>
        {[overall, ...groups].map((group, index) => (
          <tr key={`${index === 0 ? 'overall' : 'group'}-${group.key}`}>
            <GroupHeader label={group.label} overall={index === 0} />
            <Count value={group.jobs} />
            <Count value={group.queued} />
            <Count value={group.running} />
            <Count value={group.paused} />
            <Count value={group.completed} />
            <Count value={group.needs_review} />
            <Count value={group.failed_without_version} />
            <Count value={group.failed_with_version} />
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
