import type { AnnotationKind } from './comparisonSelection';
export const monitorCategoryLabels: Record<AnnotationKind, string> = {
  claim: 'Selected claims',
  identity: 'Selected identity reviews',
  relationship: 'Selected organisation relationships',
};
export function MonitorCategoryFields({
  value,
  available,
  onChange,
}: {
  value: AnnotationKind[];
  available: AnnotationKind[];
  onChange: (value: AnnotationKind[]) => void;
}) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">Meaningful-change categories</legend>
      {available.length === 0 && (
        <p className="text-xs text-muted">
          Select annotation roots to choose applicable categories.
        </p>
      )}
      {available.map((kind) => (
        <label className="flex items-center gap-2 text-sm" key={kind}>
          <input
            type="checkbox"
            checked={value.includes(kind)}
            onChange={(event) =>
              onChange(
                event.target.checked ? [...value, kind] : value.filter((item) => item !== kind),
              )
            }
          />
          {monitorCategoryLabels[kind]}
        </label>
      ))}
      <p className="text-xs text-muted">
        This monitor is pinned to one frozen report version. New evidence and confidence changes are
        observed independently by research schedules. New versions and new annotation roots are not
        added automatically.
      </p>
    </fieldset>
  );
}
