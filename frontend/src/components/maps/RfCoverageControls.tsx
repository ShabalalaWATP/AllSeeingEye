import type { RfDraft } from '@/lib/map/rfDraft';
import { useId } from 'react';

/** Study inputs invalidate analysis. Shading is a display preference only. */
export function RfCoverageControls({
  draft,
  hasReceiver,
  onChange,
  bubble,
  onBubbleChange,
}: {
  draft: RfDraft;
  hasReceiver: boolean;
  onChange: (draft: RfDraft) => void;
  bubble: boolean;
  onBubbleChange: (value: boolean) => void;
}) {
  const bubbleId = useId();
  const study = draft.study ?? (hasReceiver ? 'link' : 'area');
  const terrain = (draft.propagation ?? 'terrain') === 'terrain';
  return (
    <fieldset className="space-y-3 border-y border-line py-3">
      <legend className="pr-2 font-mono text-[10px] uppercase tracking-widest text-muted">
        Study area
      </legend>
      <div className="grid grid-cols-2 gap-1 rounded-lg bg-black/40 p-1">
        {(['link', 'area'] as const).map((id) => (
          <button
            key={id}
            type="button"
            aria-pressed={study === id}
            onClick={() => onChange({ ...draft, study: id })}
            className={`min-h-11 rounded-md border px-2 text-xs ${
              study === id
                ? 'border-cyan/40 bg-cyan/10 text-cyan'
                : 'border-transparent text-muted hover:bg-white/5 hover:text-text'
            }`}
          >
            {id === 'link' ? 'Transmitter → receiver' : '360° area'}
          </button>
        ))}
      </div>
      <p className="text-xs leading-relaxed text-muted">
        {study === 'link'
          ? 'Place both sites to inspect the direct radio path and its distance.'
          : terrain
            ? 'Screen all directions using 24 terrain bearings. The same antenna gain and receiver height apply to every target; no directional antenna pattern is modelled.'
            : 'Estimate a non-directional radius from the transmitter using the ideal horizon and receiver sensitivity.'}
      </p>
      {study === 'area' && (
        <div className="flex items-start gap-3 rounded-md border border-line p-3">
          <input
            id={bubbleId}
            type="checkbox"
            checked={bubble}
            onChange={(event) => onBubbleChange(event.target.checked)}
            className="mt-0.5 size-4 accent-cyan"
          />
          <span>
            <label htmlFor={bubbleId} className="block cursor-pointer font-medium text-text">
              Show estimated coverage bubble
            </label>
            <span className="mt-1 block text-[11px] leading-relaxed text-muted">
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
