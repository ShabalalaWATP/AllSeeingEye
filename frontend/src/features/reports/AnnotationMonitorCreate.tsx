import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { createAnnotationMonitor } from '@/lib/api/annotationMonitors';
import type { AnnotationMonitor, MonitorCreate } from '@/lib/api/annotationMonitors';
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
  const [mode, setMode] = useState<NonNullable<MonitorCreate['mode']>>('selected_roots');
  const inventoryMode = mode === 'report_inventory';
  const [name, setName] = useState('');
  const [selected, setSelected] = useState<ComparisonAnnotation[]>([]);
  const [categories, setCategories] = useState<AnnotationKind[]>([]);
  const [notify, setNotify] = useState(false);
  const [inventory, setInventory] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const request = useScopedRequest();
  const available: AnnotationKind[] = inventoryMode
    ? ['claim', 'identity', 'relationship']
    : [...new Set(selected.map(annotationKind))];
  const choose = (next: ComparisonAnnotation[]) => {
    setSelected(next);
    setCategories((previous) =>
      previous.filter((kind) => next.some((item) => annotationKind(item) === kind)),
    );
  };
  const save = async () => {
    if (busy || !name.trim() || (!inventoryMode && !selected.length) || !categories.length) return;
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const monitor = await createAnnotationMonitor(
        {
          mode,
          name: name.trim(),
          selection: toComparisonSelection({
            reportId,
            version,
            annotations: inventoryMode ? [] : selected,
          }),
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
        Choose selected annotations or the whole annotation inventory of this exact saved report
        version. Creation establishes a silent baseline, with no initial alert. The monitoring mode
        cannot be changed later. Source assertions remain separate from operator assessments.
      </p>
      <fieldset disabled={busy} className="space-y-4">
        <TextField
          label="Monitor name"
          value={name}
          maxLength={120}
          required
          onChange={(event) => setName(event.target.value)}
        />
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">What should this monitor watch?</legend>
          <label className="flex gap-2 text-sm">
            <input
              type="radio"
              name="monitor-mode"
              checked={!inventoryMode}
              onChange={() => {
                setMode('selected_roots');
                setSelected([]);
                setCategories([]);
                setError(null);
              }}
            />
            Selected annotations
          </label>
          <label className="flex gap-2 text-sm">
            <input
              type="radio"
              name="monitor-mode"
              checked={inventoryMode}
              onChange={() => {
                setMode('report_inventory');
                setSelected([]);
                setCategories([]);
                setError(null);
              }}
            />
            Whole saved report inventory
          </label>
        </fieldset>
        {inventoryMode ? (
          <p className="text-sm text-muted">
            Watch all current and future claims, identity reviews and organisation relationships in
            version {version}, including when there are no annotations yet. Creation captures the
            whole current inventory in one baseline. Up to 20 annotations in total can be monitored.
            If the inventory grows beyond 20, monitoring becomes unavailable and retains its
            previous baseline; nothing is silently truncated.
          </p>
        ) : (
          <ComparisonRevisionPicker
            key={inventory}
            latestOnly
            reportId={reportId}
            version={version}
            selected={selected}
            onChange={choose}
          />
        )}
        <MonitorCategoryFields
          inventory={inventoryMode}
          available={available}
          value={categories}
          onChange={setCategories}
        />
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
        <Button
          type="submit"
          disabled={!name.trim() || (!inventoryMode && !selected.length) || !categories.length}
        >
          Create silent baseline
        </Button>
      </fieldset>
      {error !== null && (
        <>
          <Alert tone="error">{describeError(error)}</Alert>
          <p className="text-xs text-muted">
            {inventoryMode
              ? 'Check the report remains accessible and contains no more than 20 annotation roots. No partial inventory baseline is created.'
              : 'A selected revision may have changed. Refresh the inventory and choose current revisions before trying again.'}
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
            {inventoryMode
              ? 'Clear inventory choices and retry'
              : 'Refresh inventory and clear selections'}
          </Button>
        </>
      )}
    </form>
  );
}
