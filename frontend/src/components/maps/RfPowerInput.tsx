import { useState } from 'react';
/** Retain incomplete watt edits while dBm remains the canonical planning value. */
export function RfPowerInput({
  dbm,
  onChange,
  disabled = false,
}: {
  dbm: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const [edit, setEdit] = useState<{ dbm: string; watts: string } | null>(null);
  const watts =
    edit?.dbm === dbm
      ? edit.watts
      : dbm.trim() && Number.isFinite(Number(dbm))
        ? String(Number((10 ** ((Number(dbm) - 30) / 10)).toPrecision(10)))
        : '';
  return (
    <div className="rf-power-input">
      <label className="rf-field">
        <span>Transmit power (watts)</span>
        <input
          type="number"
          disabled={disabled}
          min="0"
          step="any"
          value={watts}
          onChange={(event) => {
            const raw = event.target.value;
            const value = Number(raw);
            const next = raw.trim() && value > 0 ? String(30 + 10 * Math.log10(value)) : '';
            setEdit({ dbm: next, watts: raw });
            onChange(next);
          }}
        />
      </label>
      {disabled && (
        <p className="rf-help">
          Power is not used by the skywave geometry scenario. Choose HF groundwave or terrain
          analysis to estimate received signal strength.
        </p>
      )}
    </div>
  );
}
