import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { createAnnotationMonitor } from '@/lib/api/annotationMonitors';
import type { AnnotationMonitor } from '@/lib/api/annotationMonitors';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { ComparisonRevisionPicker } from './ComparisonRevisionPicker';
import { MonitorCategoryFields } from './MonitorCategoryFields';
import { annotationKind, toComparisonSelection } from './comparisonSelection';
import type { AnnotationKind, ComparisonAnnotation } from './comparisonSelection';

export function AnnotationMonitorCreate({
  reportId,
  version,
  onCreated,
}: {
  reportId: string;
  version: number;
  onCreated: (monitor: AnnotationMonitor) => void;
}) {
  const [name, setName] = useState('');
  const [selected, setSelected] = useState<ComparisonAnnotation[]>([]);
  const [categories, setCategories] = useState<AnnotationKind[]>([]);
  const [notify, setNotify] = useState(false);
  const [inventory, setInventory] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const request = useScopedRequest();
  const available = [...new Set(selected.map(annotationKind))];
  const choose = (next: ComparisonAnnotation[]) => {
    setSelected(next);
    setCategories((previous) =>
      previous.filter((kind) => next.some((item) => annotationKind(item) === kind)),
    );
  };
  const save = async () => {
    if (busy || !name.trim() || !selected.length || !categories.length) return;
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const monitor = await createAnnotationMonitor(
        {
          name: name.trim(),
          selection: toComparisonSelection({ reportId, version, annotations: selected }),
          categories,
          notify_on_change: notify,
        },
        signal,
      );
      signal.throwIfAborted();
      onCreated(monitor);
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  return (
    <form
      aria-label="Create annotation monitor"
      className="space-y-4 rounded border border-line p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <h3 className="font-medium">Choose what to monitor, version {version}</h3>
      <p className="text-sm text-muted">
        This is opt-in monitoring of selected annotation roots. Creation establishes a silent
        baseline, with no initial alert. Source assertions remain separate from operator
        assessments.
      </p>
      <fieldset disabled={busy} className="space-y-4">
        <TextField
          label="Monitor name"
          value={name}
          maxLength={120}
          required
          onChange={(event) => setName(event.target.value)}
        />
        <ComparisonRevisionPicker
          key={inventory}
          latestOnly
          reportId={reportId}
          version={version}
          selected={selected}
          onChange={choose}
        />
        <MonitorCategoryFields available={available} value={categories} onChange={setCategories} />
        <label className="flex gap-2 text-sm">
          <input
            type="checkbox"
            checked={notify}
            onChange={(event) => setNotify(event.target.checked)}
          />
          Create alerts for meaningful changes
        </label>
        <p className="text-xs text-muted">
          Alerts follow this report's access scope. Team workspace alerts are shared with authorised
          team members.
        </p>
        <Button type="submit" disabled={!name.trim() || !selected.length || !categories.length}>
          Create silent baseline
        </Button>
      </fieldset>
      {error !== null && (
        <>
          <Alert tone="error">{describeError(error)}</Alert>
          <p className="text-xs text-muted">
            A selected revision may have changed. Refresh the inventory and choose current revisions
            before trying again.
          </p>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => {
              setSelected([]);
              setCategories([]);
              setInventory((value) => value + 1);
              setError(null);
            }}
          >
            Refresh inventory and clear selections
          </Button>
        </>
      )}
    </form>
  );
}
