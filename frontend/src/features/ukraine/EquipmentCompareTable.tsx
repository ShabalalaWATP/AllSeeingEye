import { Table, Td, Th } from '@/components/ui/Table';
import { SIDE_LABELS, type EquipmentEntry } from '@/lib/api/ukraine';

import { formatDate } from './forceTree';

/** The same entries as a table, so the two sides can be read against each other. */
export function EquipmentCompareTable({
  entries,
  label,
}: {
  entries: readonly EquipmentEntry[];
  label: string;
}) {
  return (
    <Table caption={label}>
      <thead>
        <tr>
          <Th>Side</Th>
          <Th>System</Th>
          <Th>Origin</Th>
          <Th>Role</Th>
          <Th>Numbers (reported)</Th>
          <Th>As of</Th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <tr key={entry.id}>
            <Td>{SIDE_LABELS[entry.side]}</Td>
            <Td>{entry.name}</Td>
            <Td>{entry.origin}</Td>
            <Td>{entry.role}</Td>
            <Td>{entry.numbers ?? 'Not stated'}</Td>
            <Td>{formatDate(entry.as_of)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
