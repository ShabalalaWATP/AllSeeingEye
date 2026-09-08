import { Fragment, useSyncExternalStore } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import type { ResearchInputProps } from './ResearchInput';
import { SecSearchFields } from './SecSearchFields';
import { SecFilingResults } from './SecFilingResults';
import { InputProvenanceDeclarations } from './InputProvenanceDeclarations';
import { SecAttachmentSummary } from './SecAttachmentSummary';
import { useSecFilingInput } from './useSecFilingInput';
function Contents(props: ResearchInputProps) {
  const input = useSecFilingInput(props);
  const isAdmin = useAuthStore((state) => state.user?.role === 'admin');
  const disabled = props.disabled === true || input.busy !== null || input.declarationBusy;
  return (
    <section
      aria-label="SEC filing document discovery"
      className="space-y-4 border-t border-line pt-4"
    >
      <h2 className="font-semibold">Research an SEC filing document</h2>
      <p className="text-sm text-muted">
        Find public corporate filings by CIK, inspect their metadata, then import one primary
        document for analysis. No SEC account or API key is required. Access depends on this
        installation's administrator-configured SEC contact and source settings.
      </p>
      <SecSearchFields
        value={input.draft}
        onChange={input.edit}
        disabled={disabled || input.attached !== null}
      />
      <p className="text-xs text-muted">
        Filing dates must be from 1994 through today, spanning at most ten years. Each request
        checks one submissions file, with up to 20 selectable filings. Older-file coverage is
        bounded; review returned limitations.
      </p>
      <Button
        variant="secondary"
        disabled={disabled || input.attached !== null}
        onClick={() => void input.search()}
      >
        Discover SEC filings
      </Button>
      {input.busy !== null && (
        <div className="flex items-center gap-3">
          <p role="status" className="text-sm">
            {input.busy === 'search'
              ? 'Discovering filing metadata...'
              : input.busy === 'import'
                ? 'Fetching and extracting the selected filing document...'
                : 'Downloading the temporary original...'}
          </p>
          <Button variant="secondary" onClick={input.cancel}>
            Cancel SEC request
          </Button>
        </div>
      )}
      {input.error !== null && (
        <>
          <Alert tone="error">{input.error}</Alert>
          <p className="text-xs text-muted">
            {isAdmin
              ? 'Check the SEC source controls and the server contact setting ASE_FEEDS_CONTACT if access is unavailable. Do not enter an SEC API key.'
              : 'If SEC access is unavailable, ask an administrator to check the installation source controls and SEC contact configuration.'}
          </p>
        </>
      )}
      {input.notice !== null && <Alert>{input.notice}</Alert>}
      {input.attached ? (
        <>
          <SecAttachmentSummary
            receipt={input.attached.receipt}
            originalExpiresAt={input.attached.choice.expires_at}
            disabled={props.disabled === true || input.declarationBusy}
            downloading={input.busy === 'download'}
            onDownload={() => void input.download()}
            onRemove={input.clear}
          />
          <InputProvenanceDeclarations
            key={input.attached.receipt.id}
            receipt={input.attached.receipt}
            disabled={props.disabled === true || input.busy !== null}
            onReplace={input.replaceReceipt}
            onBusy={input.setDeclarationBusy}
          />
        </>
      ) : (
        input.page && (
          <SecFilingResults
            page={input.page}
            disabled={disabled}
            onPage={(archive, offset) => void input.search(archive, offset)}
            onImport={(choice) => void input.importChoice(choice)}
          />
        )
      )}
    </section>
  );
}
export function SecFilingPicker(props: ResearchInputProps) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return (
    <Fragment key={`${actor}:${access}`}>
      <Contents {...props} />
    </Fragment>
  );
}
