import { RF_ENVIRONMENT_DEFAULTS, createRfDraft, type RfDraft } from '@/lib/map/rfDraft';
import { RfPresetSelect } from './RfPresetSelect';
import { RfModelSummary } from './RfModelControls';
export function RfPresetControls({
  currentDraft,
  update,
}: {
  currentDraft: RfDraft;
  update: (draft: RfDraft) => void;
}) {
  const presetId = currentDraft.presetId;
  return (
    <>
      <RfPresetSelect
        presetId={presetId}
        onSelect={(selected) => {
          update({
            ...currentDraft,
            values: createRfDraft(selected.values, selected.id).values,
            presetId: selected.id,
            ...(selected.id !== 'custom'
              ? {
                  automaticHfMode:
                    selected.propagation === 'hf-skywave'
                      ? ('hf-skywave' as const)
                      : ('hf-groundwave' as const),
                }
              : {}),
            propagation:
              selected.id === 'custom' || currentDraft.propagation === 'free-space'
                ? (currentDraft.propagation ?? 'automatic')
                : 'automatic',
            environment: {
              ...RF_ENVIRONMENT_DEFAULTS,
              ...currentDraft.environment,
              ...selected.environment,
            },
          });
        }}
      />
      <RfModelSummary draft={currentDraft} />
    </>
  );
}
