import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import type { MapState } from '@/lib/api/mapViews';
import type { useSavedMapViews } from './useSavedMapViews';
import { mapRevisionLink } from './savedMapState';

export function SavedMapControls({
  saved,
  state,
  scopeLabel,
  canCreate,
  canEdit,
  blocked,
}: {
  saved: ReturnType<typeof useSavedMapViews>;
  state: MapState;
  scopeLabel: string;
  canCreate: boolean;
  canEdit: boolean;
  blocked: string | null;
}) {
  const valid = saved.title.trim().length > 0 && saved.title.length <= 200;
  return (
    <section aria-label="Saved map views" className="space-y-3 border-t border-line pt-3">
      <h3 className="font-medium">Saved map views</h3>
      <p className="text-xs text-muted">
        Saving uploads all local overlays and map settings to {scopeLabel}. They remain separate
        from report evidence. Each save creates an immutable revision; basemap tiles remain
        provider-managed cartography.
      </p>
      <TextField
        label="Map view title"
        value={saved.title}
        maxLength={200}
        onChange={(event) => saved.setTitle(event.target.value)}
      />
      {blocked && <Alert tone="warning">{blocked}</Alert>}
      {saved.error && (
        <Alert tone="error">
          {saved.error} Your current map settings remain available. For a revision conflict, reload
          the saved view or save a separate copy.
        </Alert>
      )}
      {saved.notice && (
        <p role="status" className="text-sm">
          {saved.notice}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {canCreate && (
          <Button
            variant="secondary"
            disabled={!valid || !!blocked || saved.busy}
            onClick={() => void saved.save(state, true)}
          >
            {saved.active ? 'Save separate copy' : 'Save map view'}
          </Button>
        )}
        {saved.active && canEdit && !saved.active.view.archived && (
          <>
            <Button
              variant="secondary"
              disabled={!valid || !!blocked || saved.busy}
              onClick={() => void saved.save(state, false)}
            >
              Save new revision
            </Button>
            <Button variant="ghost" disabled={saved.busy} onClick={() => void saved.archive()}>
              Archive view
            </Button>
          </>
        )}
        <Button variant="ghost" busy={saved.busy} onClick={() => void saved.browse()}>
          Browse saved views
        </Button>
      </div>
      {saved.active && (
        <a className="block text-sm underline" href={mapRevisionLink(saved.active)}>
          Open saved revision {saved.active.revision.number} of {saved.active.revision.title}
          {saved.active.view.archived ? ' (archived)' : ''}
        </a>
      )}
      {saved.page && (
        <div className="space-y-2">
          {saved.page.items.length === 0 ? (
            <p className="text-sm text-muted">No saved views on this page.</p>
          ) : (
            <ul className="space-y-2">
              {saved.page.items.map((item) => (
                <li key={item.view.id}>
                  <a
                    className="text-sm underline"
                    href={`/reports/${encodeURIComponent(item.view.report_id)}?version=${item.report_version_number}&map_view=${encodeURIComponent(item.view.id)}&map_revision=${encodeURIComponent(item.view.latest_revision_id)}`}
                  >
                    {item.title}, revision {item.revision_number}, report version{' '}
                    {item.report_version_number}
                  </a>
                </li>
              ))}
            </ul>
          )}
          <nav aria-label="Saved map pages" className="flex gap-2">
            <Button
              variant="ghost"
              disabled={saved.busy || saved.page.offset === 0}
              onClick={() => void saved.browse(Math.max(0, (saved.page?.offset ?? 0) - 20))}
            >
              Previous views
            </Button>
            <Button
              variant="ghost"
              disabled={saved.busy || saved.page.offset + 20 >= saved.page.total}
              onClick={() => void saved.browse((saved.page?.offset ?? 0) + 20)}
            >
              Next views
            </Button>
          </nav>
        </div>
      )}
    </section>
  );
}
