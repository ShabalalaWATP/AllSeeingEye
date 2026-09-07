import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import type { AnnotationMonitor, MonitorUpdate } from '@/lib/api/annotationMonitors';
import { MonitorCategoryFields } from './MonitorCategoryFields';
import type { AnnotationKind } from './comparisonSelection';
export function MonitorConfiguration({
  monitor,
  busy,
  onSave,
}: {
  monitor: AnnotationMonitor;
  busy: boolean;
  onSave: (body: MonitorUpdate) => void;
}) {
  const [name, setName] = useState(monitor.name);
  const [categories, setCategories] = useState(monitor.categories);
  const [notify, setNotify] = useState(monitor.notify_on_change);
  const [rebaseline, setRebaseline] = useState(false);
  const available: AnnotationKind[] = [];
  if (monitor.selection.revisions?.length) available.push('claim');
  if (monitor.selection.identity_revisions?.length) available.push('identity');
  if (monitor.selection.relationship_revisions?.length) available.push('relationship');
  const policyChanged =
    notify !== monitor.notify_on_change ||
    categories.length !== monitor.categories.length ||
    categories.some((kind) => !monitor.categories.includes(kind));
  const changed = policyChanged || name.trim() !== monitor.name;
  return (
    <form
      aria-label="Monitor configuration"
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (changed && name.trim() && categories.length && (!policyChanged || rebaseline))
          onSave({
            expected_revision: monitor.revision,
            action: 'configure',
            name: name.trim(),
            categories,
            notify_on_change: notify,
            rebaseline: policyChanged && rebaseline,
          });
      }}
    >
      <fieldset disabled={busy} className="space-y-3">
        <TextField
          label="Monitor name"
          value={name}
          maxLength={120}
          required
          onChange={(event) => setName(event.target.value)}
        />
        <MonitorCategoryFields
          available={available}
          value={categories}
          onChange={(value) => {
            setCategories(value);
            setRebaseline(false);
          }}
        />
        <label className="flex gap-2 text-sm">
          <input
            type="checkbox"
            checked={notify}
            onChange={(event) => {
              setNotify(event.target.checked);
              setRebaseline(false);
            }}
          />
          Create alerts for meaningful changes
        </label>
        <p className="text-xs text-muted">
          {monitor.team_id === null
            ? 'Alerts are visible within your personal workspace.'
            : "Alerts are shared with authorised members of this report's team workspace."}
        </p>
        {policyChanged && (
          <div className="space-y-2 rounded border border-amber/50 p-3">
            <p className="text-sm">
              Changing notification policy starts a fresh baseline and retains the current active or
              paused status. Pending corrections will not generate individual alerts. Catch up
              before changing policy if you want those changes processed first.
            </p>
            <label className="flex gap-2 text-sm">
              <input
                type="checkbox"
                checked={rebaseline}
                onChange={(event) => setRebaseline(event.target.checked)}
              />
              I confirm a fresh baseline for this notification policy, skipping pending differences.
            </label>
          </div>
        )}
        <Button
          type="submit"
          disabled={
            !changed || !name.trim() || !categories.length || (policyChanged && !rebaseline)
          }
        >
          Save monitor configuration
        </Button>
      </fieldset>
    </form>
  );
}
