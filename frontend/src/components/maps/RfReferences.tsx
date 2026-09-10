import { BOWMAN_REFERENCES } from '@/lib/map/rfPresets';
import type { RfPreset } from '@/lib/map/rfPresets';
export function RfReferences({ preset }: { preset: RfPreset | undefined }) {
  return (
    <details className="rf-disclosure rf-references">
      <summary>Public equipment references, including Bowman</summary>
      <div className="rf-disclosure-body">
        {preset?.referenceUrl && (
          <p className="my-2">
            <a
              href={preset.referenceUrl}
              target="_blank"
              rel="noreferrer"
              className="text-cyan underline"
            >
              {preset.referenceLabel ?? 'Preset source'}
            </a>
          </p>
        )}
        <p className="my-2">
          Public references describe supported bands or equipment families. They do not establish
          operational frequencies, current configurations or guaranteed range.
        </p>
        {BOWMAN_REFERENCES.map((item) => (
          <p key={item.url} className="my-3">
            <a href={item.url} target="_blank" rel="noreferrer" className="text-cyan underline">
              {item.title}
            </a>
            <span className="mt-1 block">{item.detail}</span>
          </p>
        ))}
      </div>
    </details>
  );
}
