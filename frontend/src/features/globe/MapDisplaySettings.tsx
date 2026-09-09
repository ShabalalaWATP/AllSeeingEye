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
    <section aria-label="Map appearance" className="space-y-2 border-t border-line p-3 text-xs">
      <h3 className="font-medium">Appearance and performance</h3>
      {[
        { label: 'Day and night', checked: terminator, action: onToggleTerminator },
        { label: 'Reduce graphics load', checked: lite, action: onToggleLite },
      ].map((item) => (
        <button
          key={item.label}
          type="button"
          role="switch"
          aria-label={item.label}
          aria-checked={item.checked}
          onClick={item.action}
          className="flex min-h-10 w-full items-center justify-between rounded px-2 text-left hover:bg-white/5"
        >
          <span>{item.label}</span>
          <span className={item.checked ? 'text-cyan' : 'text-muted'}>
            {item.checked ? 'On' : 'Off'}
          </span>
        </button>
      ))}
      <p className="text-muted">
        Reduced graphics turns off atmosphere, rotation and day/night shading.
      </p>
      {lite && terminator && (
        <p role="status" className="text-muted">
          Day/night is saved as on, but paused while reduced graphics is enabled.
        </p>
      )}
    </section>
  );
}
