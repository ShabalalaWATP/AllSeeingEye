import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { comparisonSources } from '@/test/comparisonHandlers';
import { report } from '@/test/fixtures';
import { ComparisonRevisionPicker } from './ComparisonRevisionPicker';
import { MonitorCategoryFields } from './MonitorCategoryFields';
import type { AnnotationKind, ComparisonAnnotation } from './comparisonSelection';

it('requires an explicit current-root selection and does not offer historical revisions for monitoring', async () => {
  comparisonSources();
  function Picker() {
    const [selected, setSelected] = useState<ComparisonAnnotation[]>([]);
    return (
      <ComparisonRevisionPicker
        latestOnly
        reportId={report.report.id}
        version={1}
        selected={selected}
        onChange={setSelected}
      />
    );
  }
  render(<Picker />);
  const checkbox = await screen.findByRole('checkbox');
  expect(checkbox).not.toBeChecked();
  expect(screen.queryByRole('button', { name: /Browse revisions/ })).not.toBeInTheDocument();
  await userEvent.click(checkbox);
  expect(screen.getByText('1 of 20 watched roots selected')).toBeInTheDocument();
  expect(screen.getByText(/New roots are not watched automatically/)).toBeInTheDocument();
});

it('offers only applicable categories and explains frozen-version limits', async () => {
  function Categories() {
    const [value, setValue] = useState<AnnotationKind[]>(['claim']);
    return (
      <MonitorCategoryFields
        value={value}
        available={['claim', 'relationship']}
        onChange={setValue}
      />
    );
  }
  render(<Categories />);
  expect(screen.queryByLabelText('Selected identity reviews')).not.toBeInTheDocument();
  await userEvent.click(screen.getByLabelText('Selected claims'));
  expect(screen.getByLabelText('Selected claims')).not.toBeChecked();
  await userEvent.click(screen.getByLabelText('Selected organisation relationships'));
  expect(screen.getByLabelText('Selected organisation relationships')).toBeChecked();
  expect(screen.getByText(/pinned to one frozen report version/)).toBeInTheDocument();
});

it('explains why no categories are available before selecting roots', () => {
  render(<MonitorCategoryFields value={[]} available={[]} onChange={() => undefined} />);
  expect(
    screen.getByText('Select annotation roots to choose applicable categories.'),
  ).toBeInTheDocument();
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
});
