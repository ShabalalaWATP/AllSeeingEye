import { Button } from '@/components/ui/Button';

export function RegionalPresets({
  onSelect,
}: {
  onSelect: (country: string, languages: string[]) => void;
}) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">Regional presets</legend>
      <p className="text-xs text-muted">
        Set the country and search languages, then adjust them below.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => onSelect('RU', ['en', 'ru'])}>
          Russia
        </Button>
        <Button variant="secondary" onClick={() => onSelect('CN', ['en', 'zh-CN', 'zh-TW'])}>
          China
        </Button>
        <Button variant="secondary" onClick={() => onSelect('IR', ['en', 'fa'])}>
          Iran
        </Button>
      </div>
    </fieldset>
  );
}
