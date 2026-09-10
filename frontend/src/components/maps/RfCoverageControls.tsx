import type { RfDraft } from '@/lib/map/rfDraft';
import { useId } from 'react';
import { resolveRfMode } from '@/lib/map/rfAutomation';
import type { RfInputs } from '@/lib/map/rfPlanning';
import { RfAreaExtent } from './RfAreaExtent';

/** Study inputs invalidate analysis. Shading is a display preference only. */
export function RfCoverageControls({
  draft,
  hasReceiver,
  onChange,
  bubble,
  onBubbleChange,
  input,
}: {
  draft: RfDraft;
  hasReceiver: boolean;
  onChange: (draft: RfDraft) => void;
  bubble: boolean;
  onBubbleChange: (value: boolean) => void;
  input: RfInputs;
}) {
  const bubbleId = useId();
  const study = draft.study ?? (hasReceiver ? 'link' : 'area');
  const mode = resolveRfMode(draft);
  const terrain = mode === 'terrain';
  return (
    <fieldset className="rf-coverage">
      <legend className="rf-section-label">Study area</legend>
      <div className="rf-study-switch">
        {(['link', 'area'] as const).map((id) => (
          <button
            key={id}
            type="button"
            aria-pressed={study === id}
            onClick={() => onChange({ ...draft, study: id })}
            className="rf-study-option"
          >
            {id === 'link' ? 'Transmitter → receiver' : '360° area'}
          </button>
        ))}
      </div>
      <p className="rf-help">
        {study === 'link'
          ? 'Place both sites to inspect the direct radio path and its distance.'
          : terrain
            ? 'Screen all directions using 24 terrain bearings. The same antenna gain and receiver height apply to every target; no directional antenna pattern is modelled.'
            : mode === 'hf-groundwave'
              ? 'Estimate groundwave reach in all directions over one assumed ground surface. Terrain and changes in ground type are not resolved.'
              : 'Estimate a non-directional radius from the transmitter using the ideal horizon and receiver sensitivity.'}
      </p>
      {study === 'area' && (terrain || mode === 'hf-groundwave') && (
        <RfAreaExtent draft={draft} input={input} onChange={onChange} />
      )}
      {study === 'area' && mode !== 'hf-groundwave' && (
        <div className="rf-bubble-setting">
          <input
            id={bubbleId}
            type="checkbox"
            checked={bubble}
            onChange={(event) => onBubbleChange(event.target.checked)}
            className="rf-checkbox"
          />
          <span>
            <label htmlFor={bubbleId} className="rf-checkbox-label">
              Show estimated coverage bubble
            </label>
            <span className="rf-help block">
              {terrain
                ? 'Shade an illustrative footprint between passing bearings. Gaps and grey rays remain unassessed.'
                : 'Shade the ideal distance estimate. Terrain and actual reception are not checked.'}
            </span>
          </span>
        </div>
      )}
    </fieldset>
  );
}
