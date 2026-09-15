import { useState } from 'react';

import { PersonCell } from '@/components/admin/PersonCell';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { Td } from '@/components/ui/Table';
import { approveAccountRequest, rejectAccountRequest } from '@/lib/api/admin';
import { describeError } from '@/lib/api/errors';
import { roleSchema } from '@/lib/api/schemas';
import type { AccountRequest, ApproveResponse, Role } from '@/lib/api/schemas';
import { formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

import { roleOptions } from './roleOptions';

export interface AccountRequestRowProps {
  request: AccountRequest;
  onApproved: (response: ApproveResponse) => void;
  onRejected: () => void;
}

export function AccountRequestRow({ request, onApproved, onRejected }: AccountRequestRowProps) {
  const [role, setRole] = useState<Role>('user');
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  const approve = useAsyncAction(async () => {
    onApproved(await approveAccountRequest(request.id, role));
  });
  const reject = useAsyncAction(async () => {
    await rejectAccountRequest(request.id, reason);
    onRejected();
  });
  const busy = approve.busy || reject.busy;
  const error = approve.error ?? reject.error;

  return (
    <tr>
      <Td className="min-w-52 py-3">
        <PersonCell name={request.display_name} email={request.email} />
      </Td>
      <Td className="max-w-sm min-w-48 py-3 leading-6">
        {request.reason ?? <span className="text-muted italic">No reason given</span>}
      </Td>
      <Td className="py-3 font-mono text-xs whitespace-nowrap text-muted">
        {formatUtc(request.created_at)}
      </Td>
      <Td className="min-w-72 py-3">
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-end gap-2">
            <SelectField
              label="Role"
              labelHidden
              options={roleOptions}
              value={role}
              disabled={busy}
              className="w-28"
              onChange={(event) => {
                setRole(roleSchema.parse(event.target.value));
              }}
            />
            <Button busy={approve.busy} disabled={busy} onClick={() => void approve.run()}>
              Approve
            </Button>
            <Button
              variant="danger"
              disabled={busy}
              aria-expanded={rejecting}
              onClick={() => {
                setRejecting((open) => !open);
              }}
            >
              Reject
            </Button>
          </div>
          {rejecting ? (
            <div className="flex flex-wrap items-end gap-2 rounded-lg border border-critical/40 bg-critical/5 p-3">
              <TextField
                label="Reason (optional)"
                name="reason"
                maxLength={500}
                value={reason}
                disabled={busy}
                hint="Up to 500 characters."
                className="w-full min-w-48 sm:w-64"
                onChange={(event) => {
                  setReason(event.target.value);
                }}
              />
              <Button
                variant="danger"
                busy={reject.busy}
                disabled={busy}
                onClick={() => void reject.run()}
              >
                Confirm rejection
              </Button>
            </div>
          ) : null}
          {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
        </div>
      </Td>
    </tr>
  );
}
