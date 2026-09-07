import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import type { EvidenceItem } from '@/lib/api/reports';
import { report } from '@/test/fixtures';
import { EvidenceNavigation } from './EvidenceLinks';
import { ReportedRelationships } from './ReportedRelationships';
import { organisationRelationships } from './organisationRelationships';

const child = '00123456789012345678';
const parent = '549300B56MD0ZC402L06';
function evidence(kind: 'direct' | 'ultimate' = 'direct'): EvidenceItem {
  return {
    ...report.version.evidence[0]!,
    label: kind === 'direct' ? 'E1' : 'E2',
    source_id: `research-gleif-${kind}-parent`,
    source_name: 'GLEIF',
    grade: 'F6',
    captured_at: '2026-09-07T12:00:00Z',
    attributes: Object.entries({
      record_kind: 'reported_accounting_consolidation',
      child_lei: child,
      parent_lei: parent,
      reported_relationship_type:
        kind === 'direct' ? 'IS_DIRECTLY_CONSOLIDATED_BY' : 'IS_ULTIMATELY_CONSOLIDATED_BY',
      reported_relationship_status: 'INACTIVE',
      reported_valid_from: 'Source date unclear',
      reported_periods: JSON.stringify([
        { type: 'RELATIONSHIP_PERIOD', startDate: '2010-01-01', endDate: '2020-01-01' },
      ]),
      reported_periods_omitted: 7,
      reported_corroboration_reference: '声明 <script>not HTML</script>',
    }).map(([key, value]) => ({ key, value })),
  };
}

it('shows separate direct and ultimate dated assertions with exact evidence links', async () => {
  const items = [evidence(), evidence('ultimate')];
  render(
    <EvidenceNavigation evidence={items}>
      <ReportedRelationships evidence={items} />
    </EvidenceNavigation>,
  );
  await userEvent.click(screen.getByText('Reported organisation relationships (2)'));
  expect(screen.getAllByText(child)).toHaveLength(2);
  expect(screen.getAllByText(parent)).toHaveLength(2);
  expect(screen.getByText('Reported direct accounting-consolidation parent')).toBeInTheDocument();
  expect(screen.getByText('Reported ultimate accounting-consolidation parent')).toBeInTheDocument();
  const first = screen.getAllByRole('article')[0]!;
  expect(within(first).getByText('INACTIVE')).toBeInTheDocument();
  expect(
    within(first).getByText('RELATIONSHIP_PERIOD: 2010-01-01 to 2020-01-01'),
  ).toBeInTheDocument();
  expect(within(first).getByText('Source date unclear')).toBeInTheDocument();
  expect(
    within(first).getByText('7 period entries were omitted during collection.'),
  ).toBeInTheDocument();
  expect(within(first).getByText('声明 <script>not HTML</script>')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'View evidence E1' })).toHaveAttribute(
    'href',
    '#evidence-E1',
  );
  expect(
    screen.getByText(/does not independently establish beneficial ownership/),
  ).toBeInTheDocument();
});

it.each(['source', 'kind', 'identifier', 'duplicate', 'missing'])(
  'does not create connections from %s metadata',
  (change) => {
    const item = evidence();
    if (change === 'source') item.source_id = 'constructor';
    else if (change === 'missing') delete item.attributes;
    else if (change === 'duplicate') item.attributes!.push({ key: 'child_lei', value: child });
    else
      item.attributes = item.attributes!.map((entry) =>
        entry.key === (change === 'kind' ? 'reported_relationship_type' : 'parent_lei')
          ? { ...entry, value: 'Invalid' }
          : entry,
      );
    expect(organisationRelationships([item]).rows).toHaveLength(0);
    render(
      <EvidenceNavigation evidence={[item]}>
        <ReportedRelationships evidence={[item]} />
      </EvidenceNavigation>,
    );
    expect(screen.getByText(/This does not establish that no parent exists/)).toBeInTheDocument();
    if (change !== 'source')
      expect(screen.getByText(/could not be displayed safely/)).toBeInTheDocument();
  },
);

it.each(['invalid-json', 'invalid-row', 'oversized', 'absent', 'empty'])(
  'preserves the assertion while disclosing %s periods',
  (change) => {
    const item = evidence();
    const value =
      change === 'invalid-json'
        ? '['
        : change === 'invalid-row'
          ? '[{"type":1}]'
          : change === 'oversized'
            ? 'x'.repeat(501)
            : '[]';
    item.attributes = item.attributes!.filter(
      (entry) => !['reported_periods', 'reported_periods_omitted'].includes(entry.key),
    );
    if (change !== 'absent') item.attributes.push({ key: 'reported_periods', value });
    render(<ReportedRelationships evidence={[item]} />);
    expect(screen.getByText('Reported direct accounting-consolidation parent')).toBeInTheDocument();
    expect(
      screen.getByText(
        change === 'empty'
          ? 'No periods were captured.'
          : 'Period metadata is missing or unreadable; inspect the original evidence.',
      ),
    ).toBeInTheDocument();
  },
);
