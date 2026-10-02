import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { findLeiCandidates, type LeiCandidate } from '@/lib/api/leiCandidates';

export function LeiCandidateLookup({
  initialName,
  disabled,
  confirm,
}: {
  initialName: string;
  disabled: boolean;
  confirm: (lei: string) => void;
}) {
  const [name, setName] = useState(initialName);
  const [country, setCountry] = useState('');
  const [items, setItems] = useState<LeiCandidate[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const clear = () => {
    controller.current?.abort();
    controller.current = null;
    setItems(null);
    setError('');
    setBusy(false);
  };
  const search = async () => {
    clear();
    const active = new AbortController();
    controller.current = active;
    setBusy(true);
    try {
      const result = await findLeiCandidates(name.trim(), country, active.signal);
      if (!active.signal.aborted) setItems(result.items);
    } catch {
      if (!active.signal.aborted) setError('GLEIF lookup failed. Try again when available.');
    } finally {
      if (!active.signal.aborted) setBusy(false);
    }
  };
  return (
    <fieldset className="space-y-2 rounded border border-line p-3">
      <legend>Find an LEI by company name</legend>
      <p className="text-xs text-muted">
        Search sends the typed company name and optional country to GLEIF, a public registry. Choose
        and confirm a candidate yourself. A name match does not establish identity.
      </p>
      <TextField
        label="Company name for GLEIF"
        value={name}
        maxLength={200}
        onChange={(event) => {
          clear();
          setName(event.target.value);
        }}
      />
      <TextField
        label="GLEIF country code (optional)"
        value={country}
        maxLength={2}
        hint="Two-letter code, for example GB."
        onChange={(event) => {
          clear();
          setCountry(event.target.value.toUpperCase());
        }}
      />
      <Button
        variant="secondary"
        disabled={
          disabled ||
          busy ||
          name.trim().length < 2 ||
          (country !== '' && !/^[A-Z]{2}$/.test(country))
        }
        onClick={() => void search()}
      >
        {busy ? 'Searching GLEIF…' : 'Search GLEIF'}
      </Button>
      {error && <p role="alert">{error}</p>}
      {items?.length === 0 && <p role="status">No candidates returned. No identifier selected.</p>}
      {items && items.length > 0 && (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.lei}>
              <p>
                {item.name} · {item.jurisdiction} · {item.status} · {item.lei}
              </p>
              <Button
                variant="secondary"
                disabled={disabled}
                onClick={() => {
                  confirm(item.lei);
                  clear();
                }}
              >
                Confirm {item.name} ({item.lei})
              </Button>
            </li>
          ))}
        </ul>
      )}
    </fieldset>
  );
}
