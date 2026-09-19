/**
 * Pin a question to one tracked conflict or one kind of natural disaster. The choices come
 * from the trackers, so a name here is a name the boards already know, and a saved value
 * the boards no longer list is kept visible rather than silently dropped.
 */
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import { fetchConflictBoard, fetchDisasterBoard } from '@/lib/api/trackers';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

async function loadFocus() {
  const [conflicts, hazards] = await Promise.all([fetchConflictBoard(), fetchDisasterBoard()]);
  return { conflicts, hazards };
}

export interface FocusChoice {
  conflictId: string;
  hazard: string;
}

export function FocusPicker({
  conflictId,
  hazard,
  onChange,
  disabled = false,
}: FocusChoice & { onChange: (value: FocusChoice) => void; disabled?: boolean }) {
  const choices = useScopedResource(loadFocus);
  if (choices.error) {
    return (
      <Alert tone="error">
        {describeError(choices.error)}{' '}
        <Button variant="secondary" onClick={() => void choices.reload()}>
          Retry choices
        </Button>
      </Alert>
    );
  }
  if (!choices.data) return <LoadingNote label="Loading conflicts and disasters" />;
  const { conflicts, hazards } = choices.data;
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <SelectField
        label="Conflict"
        hint="Follow one tracked conflict. Its countries join the scope."
        value={conflictId}
        disabled={disabled}
        onChange={(event) => onChange({ conflictId: event.target.value, hazard: '' })}
        options={[
          { value: '', label: 'Any or none' },
          ...conflicts.map(({ conflict }) => ({ value: conflict.id, label: conflict.name })),
          ...(conflictId && !conflicts.some(({ conflict }) => conflict.id === conflictId)
            ? [{ value: conflictId, label: `Saved conflict: ${conflictId}` }]
            : []),
        ]}
      />
      <SelectField
        label="Natural disaster"
        hint="Follow one kind of hazard wherever it is reported."
        value={hazard}
        disabled={disabled}
        onChange={(event) => onChange({ conflictId: '', hazard: event.target.value })}
        options={[
          { value: '', label: 'Any or none' },
          ...hazards.map((item) => ({ value: item.hazard, label: item.title })),
          ...(hazard && !hazards.some((item) => item.hazard === hazard)
            ? [{ value: hazard, label: `Saved disaster: ${hazard}` }]
            : []),
        ]}
      />
    </div>
  );
}
