import { Button } from '@/components/ui/Button';
export function MonitorPagination({
  offset,
  total,
  count,
  label,
  onChange,
}: {
  offset: number;
  total: number;
  count: number;
  label: string;
  onChange: (offset: number) => void;
}) {
  return (
    <nav aria-label={`${label} pages`} className="flex flex-wrap items-center gap-3 text-xs">
      <Button
        variant="secondary"
        disabled={offset === 0}
        onClick={() => onChange(Math.max(0, offset - 20))}
      >
        Previous {label} page
      </Button>
      <span>{count === 0 ? 'No entries' : `${offset + 1} to ${offset + count} of ${total}`}</span>
      <Button
        variant="secondary"
        disabled={offset + 20 >= total}
        onClick={() => onChange(offset + 20)}
      >
        Next {label} page
      </Button>
    </nav>
  );
}
