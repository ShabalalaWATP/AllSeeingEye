import { memo } from 'react';
import { MapControlIcon, type ControlIcon } from './MapControlIcon';
import { MapControlLabel } from './MapControlLabel';

/** Panel content can change without rebuilding its unchanged rail entry. */
export const MapToolButton = memo(function MapToolButton({
  label,
  icon,
  caption,
  on,
  active,
  expanded,
  controls,
  onOpen,
  onChoose,
}: {
  label: string;
  icon: ControlIcon;
  caption: string | undefined;
  on: boolean | undefined;
  active: boolean;
  expanded: boolean;
  controls: string | undefined;
  onOpen: (() => void) | undefined;
  onChoose: (label: string, onOpen: (() => void) | undefined, button?: HTMLButtonElement) => void;
}) {
  return (
    <MapControlLabel label={label}>
      <button
        type="button"
        className={`map-icon-button ${caption ? 'map-style-button' : ''}`}
        aria-label={label}
        title={label}
        aria-expanded={expanded}
        aria-controls={controls}
        data-on={on ? 'true' : undefined}
        data-active={active ? 'true' : undefined}
        onClick={(event) => onChoose(label, onOpen, event.currentTarget)}
      >
        <MapControlIcon name={icon} />
        {caption && <span className="map-style-label">{caption}</span>}
      </button>
    </MapControlLabel>
  );
});
