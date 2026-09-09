import { useState } from 'react';
/** Retain incomplete watt edits while dBm remains the canonical planning value. */
export function RfPowerInput({
  dbm,
  onChange,
}: {
  dbm: string;
  onChange: (value: string) => void;
}) {
  const [edit, setEdit] = useState<{ dbm: string; watts: string } | null>(null);
  const watts =
    edit?.dbm === dbm
      ? edit.watts
      : dbm.trim() && Number.isFinite(Number(dbm))
        ? String(Number((10 ** ((Number(dbm) - 30) / 10)).toPrecision(10)))
        : '';
  return (
    <label className="block text-muted">
      Transmit power (W)
      <input
        type="number"
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
        className="mt-1 w-full rounded border border-line bg-ground p-2 text-text"
      />
    </label>
  );
}
