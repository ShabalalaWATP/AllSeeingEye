/**
 * axe checks on the shared UI primitives in the states readers meet them (KAN-61): busy
 * buttons, an open confirmation, a field error summary, invalid fields, alerts, an empty
 * state and a table. Each renders inside a minimal page (`main` and one `h1`) so the
 * page-level rules apply as they would in the shell. See `src/test/axe.ts` for jsdom's limits.
 */
import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, it } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { useFieldErrors } from '@/lib/api/fieldErrors';
import { expectNoAxeViolations } from '@/test/axe';
import { installDialogStub } from '@/test/dialogStub';

import { Alert, LoadingNote } from './Alert';
import { Button } from './Button';
import { ConfirmDialog } from './ConfirmDialog';
import { EmptyState } from './EmptyState';
import { SelectField, TextAreaField, TextField } from './Field';
import { FormErrors } from './FormErrors';
import { Table, Td, Th } from './Table';

installDialogStub();

function Page({ children }: { children: ReactNode }) {
  return (
    <main>
      <h1>Primitives</h1>
      {children}
    </main>
  );
}

function InvalidForm() {
  const errors = useFieldErrors(
    new ApiError(422, 'validation_error', 'The request is invalid.', {
      name: 'Enter a name.',
      notes: 'Notes are too long.',
    }),
    { name: 'Name', notes: 'Notes' },
  );
  return (
    <form aria-label="Example">
      <FormErrors errors={errors} />
      <TextField label="Name" hint="As it appears on the report." {...errors.field('name')} />
      <TextAreaField label="Notes" {...errors.field('notes')} />
      <SelectField
        label="Scope"
        options={[
          { value: 'personal', label: 'Personal' },
          { value: 'team', label: 'Team' },
        ]}
      />
    </form>
  );
}

describe('shared primitives have no axe violations', () => {
  it('buttons in every variant, including busy and disabled', async () => {
    render(
      <Page>
        <Button>Save</Button>
        <Button variant="secondary" busy>
          Saving
        </Button>
        <Button variant="danger" disabled>
          Delete
        </Button>
        <Button variant="ghost">Cancel</Button>
      </Page>,
    );
    await expectNoAxeViolations();
  });

  it('a form with an error summary, hints and invalid fields', async () => {
    render(
      <Page>
        <InvalidForm />
      </Page>,
    );
    await expectNoAxeViolations();
  });

  it('alerts, a loading note and an empty state', async () => {
    render(
      <Page>
        <Alert tone="error" title="Could not save">
          Try again.
        </Alert>
        <Alert tone="success">Saved.</Alert>
        <LoadingNote label="Loading reports" />
        <EmptyState
          title="No reports yet"
          purpose="Saved research appears here."
          action={<a href="/research">Start research</a>}
        />
      </Page>,
    );
    await expectNoAxeViolations();
  });

  it('a table with a caption and column headings', async () => {
    render(
      <Page>
        <Table caption="Members" stickyHeader>
          <thead>
            <tr>
              <Th>Name</Th>
              <Th>Role</Th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <Td>Uma User</Td>
              <Td>Member</Td>
            </tr>
          </tbody>
        </Table>
      </Page>,
    );
    await expectNoAxeViolations();
  });

  it('an open confirmation, including a failed attempt', async () => {
    render(
      <Page>
        <ConfirmDialog
          open
          title="Delete report “Kyiv grid”?"
          confirmLabel="Delete report"
          busyLabel="Deleting"
          tone="danger"
          busy={false}
          error="The report could not be deleted."
          onConfirm={() => undefined}
          onCancel={() => undefined}
        >
          This cannot be undone.
        </ConfirmDialog>
      </Page>,
    );
    await expectNoAxeViolations();
  });
});
