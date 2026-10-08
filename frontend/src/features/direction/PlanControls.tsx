import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { AreaOfInterest, CollectionPlan } from '@/lib/api/direction';

interface AreasState {
  data: readonly AreaOfInterest[] | null;
  error: unknown;
  reload: () => unknown;
}

/** Edit and delete for one plan, shared by its evidence view and its repair view. */
export function PlanActions({
  plan,
  manageable,
  editing,
  areas,
  onEdit,
  onDelete,
}: {
  plan: CollectionPlan;
  manageable: boolean;
  editing: boolean;
  areas: AreasState;
  onEdit: (plan: CollectionPlan, areas: readonly AreaOfInterest[]) => void;
  onDelete: (plan: CollectionPlan) => void;
}) {
  return (
    <>
      <Button
        variant="secondary"
        disabled={!manageable || editing || areas.data === null}
        onClick={() => {
          if (areas.data !== null) onEdit(plan, areas.data);
        }}
      >
        Edit plan
      </Button>
      <Button
        disabled={!manageable}
        variant="danger"
        aria-haspopup="dialog"
        onClick={() => onDelete(plan)}
      >
        Delete plan
      </Button>
    </>
  );
}

/** Why editing is unavailable when the area list failed, beside a retry. */
export function AreasUnavailable({
  areas,
  manageable,
}: {
  areas: AreasState;
  manageable: boolean;
}) {
  if (areas.error === null || !manageable) return null;
  return (
    <Alert tone="error">
      Areas could not be loaded, so the plan cannot be edited yet.{' '}
      <Button variant="secondary" onClick={() => void areas.reload()}>
        Retry areas
      </Button>
    </Alert>
  );
}
