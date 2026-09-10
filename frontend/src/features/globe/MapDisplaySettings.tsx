import '@/components/maps/mapTool.css';
import './referenceTools.css';

/** Appearance has one owner, beside basemap choices on the right. */
export function MapDisplaySettings({
  terminator,
  lite,
  onToggleTerminator,
  onToggleLite,
}: {
  terminator: boolean;
  lite: boolean;
  onToggleTerminator: () => void;
  onToggleLite: () => void;
}) {
  return (
    <section aria-label="Map appearance" className="map-tool-workspace map-reference-appearance">
      <h3 className="map-tool-section-title">Appearance and performance</h3>
      {[
        {
          label: 'Day and night',
          description: 'Show the sunlit and dark sides of the Earth.',
          checked: terminator,
          action: onToggleTerminator,
        },
        {
          label: 'Reduce graphics load',
          description: 'Turn off atmosphere, rotation and day/night shading.',
          checked: lite,
          action: onToggleLite,
        },
      ].map((item) => (
        <button
          key={item.label}
          type="button"
          role="switch"
          aria-label={item.label}
          aria-checked={item.checked}
          onClick={item.action}
          className="map-reference-switch"
        >
          <span>
            <span className="map-reference-switch-title">{item.label}</span>
            <span className="map-tool-help">{item.description}</span>
          </span>
          <span aria-hidden="true" className="map-reference-toggle" />
        </button>
      ))}
      {lite && terminator && (
        <p role="status" className="map-tool-notice">
          Day/night is saved as on, but paused while reduced graphics is enabled.
        </p>
      )}
    </section>
  );
}
