import { CAMERA_MEDIA_CHOICES, type CameraMediaKind } from './cameraMediaFilters';

export function CameraMediaFilter({
  kind,
  setKind,
}: {
  kind: CameraMediaKind;
  setKind: (value: CameraMediaKind) => void;
}) {
  return (
    <fieldset className="space-y-2">
      <legend className="font-medium">Camera media</legend>
      <div className="grid grid-cols-2 gap-1">
        {CAMERA_MEDIA_CHOICES.map(({ value, label }) => (
          <label
            key={value}
            className={`flex min-h-11 cursor-pointer items-center gap-2 rounded px-2 ${kind === value ? 'bg-cyan/10 text-cyan' : 'text-muted hover:bg-white/5'}`}
          >
            <input
              type="radio"
              name="camera-media"
              value={value}
              checked={kind === value}
              onChange={() => setKind(value)}
              className="accent-cyan"
            />
            {label}
          </label>
        ))}
      </div>
      <p className="text-[11px] leading-relaxed text-muted">
        Filters the list and map. Clips are recordings; streams may be delayed or offline. Provider
        links have no approved in-app media. Previews load only when requested.
      </p>
    </fieldset>
  );
}
