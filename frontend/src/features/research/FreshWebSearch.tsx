export function FreshWebSearch({
  enabled,
  onChange,
}: {
  enabled: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-3 border-y border-line py-4">
      <input
        type="checkbox"
        checked={enabled}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-1 h-4 w-4 shrink-0 accent-ember"
      />
      <span className="text-sm font-medium">
        Fresh web search
        <span className="mt-1 block text-xs font-normal leading-relaxed text-muted">
          Also ask the selected AI search provider to search the public web using your question,
          countries and dates. Results are combined with app sources and linked in the report.
          Requires a compatible, configured AI connection.
        </span>
        {enabled && (
          <span className="mt-2 block text-xs font-normal text-ember">
            Your question and scope will be sent to that provider. Search results may have
            incomplete dates or geographic coverage.
          </span>
        )}
      </span>
    </label>
  );
}
