import { Button } from '@/components/ui/Button';
import { ConfirmButton } from '@/components/ui/ConfirmButton';
import { CopyButton } from '@/components/ui/CopyButton';
import type { Enquiry, EnquiryStatus } from '@/lib/api/enquiries';
import { formatUtc } from '@/lib/format';

const DEPLOYMENT = {
  own_cloud: 'Own cloud',
  on_premises: 'On premises',
  air_gapped: 'Air-gapped',
  undecided: 'Undecided',
} as const;
const USERS = {
  '1_10': '1 to 10',
  '11_50': '11 to 50',
  '51_250': '51 to 250',
  '250_plus': '250 or more',
} as const;

export function EnquiryCard({
  item,
  busy,
  disabled,
  change,
}: {
  item: Enquiry;
  busy: boolean;
  disabled: boolean;
  change: (id: string, next: EnquiryStatus | 'delete') => Promise<void>;
}) {
  return (
    <li
      aria-labelledby={`enquiry-${item.id}`}
      className="min-w-0 space-y-3 rounded-lg border border-line p-4"
    >
      <h3 id={`enquiry-${item.id}`} className="break-words font-semibold">
        {item.organisation}
      </h3>
      <dl className="grid min-w-0 grid-cols-1 gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-muted">Contact</dt>
          <dd className="break-words">
            {item.name}
            {item.role ? `, ${item.role}` : ''}
          </dd>
        </div>
        <div>
          <dt className="text-muted">Work email</dt>
          <dd className="break-all">{item.email}</dd>
        </div>
        <div>
          <dt className="text-muted">Deployment interest</dt>
          <dd>{DEPLOYMENT[item.deployment_interest]}</dd>
        </div>
        <div>
          <dt className="text-muted">Expected users</dt>
          <dd>{USERS[item.expected_users]}</dd>
        </div>
        <div>
          <dt className="text-muted">Received</dt>
          <dd>{formatUtc(item.created_at)}</dd>
        </div>
        <div>
          <dt className="text-muted">Status</dt>
          <dd className="capitalize">{item.status}</dd>
        </div>
      </dl>
      {item.message ? (
        <details>
          <summary className="cursor-pointer text-sm underline">Read message</summary>
          <p className="mt-2 whitespace-pre-wrap break-words text-sm">{item.message}</p>
        </details>
      ) : (
        <p className="text-sm text-muted">No message supplied.</p>
      )}
      <div className="flex flex-wrap gap-2">
        <CopyButton value={item.email} label="Copy email" />
        {item.status !== 'contacted' && (
          <Button
            variant="secondary"
            disabled={disabled}
            onClick={() => void change(item.id, 'contacted')}
          >
            Mark contacted
          </Button>
        )}
        {item.status !== 'closed' && (
          <Button
            variant="secondary"
            disabled={disabled}
            onClick={() => void change(item.id, 'closed')}
          >
            Close enquiry
          </Button>
        )}
        <ConfirmButton
          label="Delete"
          busy={busy}
          disabled={disabled}
          title="Permanently delete enquiry?"
          confirmLabel="Delete permanently"
          busyLabel="Deleting…"
          onConfirm={() => void change(item.id, 'delete')}
        >
          <p className="break-words">
            This permanently erases the enquiry from {item.organisation}. It cannot be undone.
            Operator email copies and backups require separate handling.
          </p>
        </ConfirmButton>
      </div>
    </li>
  );
}
