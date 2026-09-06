import { SelectField, TextField } from '@/components/ui/Field';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import type { Country } from '@/lib/api/geoSchemas';
import type { ReportRequest } from '@/lib/api/reports';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

export const languages = [
  ['en', 'English'],
  ['fr', 'French'],
  ['de', 'German'],
  ['es', 'Spanish'],
  ['ar', 'Arabic'],
  ['ru', 'Russian'],
  ['uk', 'Ukrainian'],
  ['zh', 'Chinese'],
] as const;

export type ResearchFocus = ReportRequest['research_focus'];

interface ScopeProps {
  workspaces: Workspaces;
  teamId: string;
  selectTeam: (id: string) => void;
  countries: readonly Country[];
  country: string;
  setCountry: (value: string) => void;
  windowHours: string;
  setWindowHours: (value: string) => void;
  selectedLanguages: string[];
  setLanguages: (value: string[]) => void;
  focus: ResearchFocus;
  setFocus: (value: ResearchFocus) => void;
  subject: string;
  setSubject: (value: string) => void;
}

export function ResearchScope(props: ScopeProps) {
  const knownCountry =
    !props.country || props.countries.some((item) => item.iso2 === props.country);
  return (
    <div className="grid min-w-0 gap-5 pt-4">
      <WorkspaceField
        workspaces={props.workspaces}
        value={props.teamId}
        onChange={props.selectTeam}
      />
      <div className="grid gap-5 sm:grid-cols-2">
        {props.focus === 'general' && (
          <SelectField
            label="Country"
            value={props.country}
            onChange={(event) => props.setCountry(event.target.value)}
            className="min-h-11"
            options={[
              { value: '', label: 'All countries' },
              ...(!knownCountry
                ? [{ value: props.country, label: `Unavailable country: ${props.country}` }]
                : []),
              ...props.countries.map((item) => ({ value: item.iso2, label: item.name })),
            ]}
          />
        )}
        <SelectField
          label="Reporting window"
          value={props.windowHours}
          onChange={(event) => props.setWindowHours(event.target.value)}
          className="min-h-11"
          options={[
            { value: '24', label: 'Past 24 hours' },
            { value: '72', label: 'Past 3 days' },
            { value: '168', label: 'Past 7 days' },
            { value: '336', label: 'Past 14 days' },
          ]}
        />
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <SelectField
          label="Research focus"
          value={props.focus}
          className="min-h-11"
          options={[
            { value: 'general', label: 'General question' },
            { value: 'company', label: 'Company' },
            { value: 'domain', label: 'Domain' },
            { value: 'document', label: 'Private document' },
            { value: 'media', label: 'Private media' },
          ]}
          onChange={(event) => {
            const value = event.target.value;
            if (
              value === 'general' ||
              value === 'company' ||
              value === 'domain' ||
              value === 'document' ||
              value === 'media'
            )
              props.setFocus(value);
          }}
        />
        {(props.focus === 'company' || props.focus === 'domain') && (
          <TextField
            label={props.focus === 'company' ? 'Company name' : 'Domain name'}
            className="min-h-11"
            maxLength={300}
            value={props.subject}
            onChange={(event) => props.setSubject(event.target.value)}
            hint={
              props.focus === 'company'
                ? 'Use the full name, including its country if needed.'
                : 'For example, example.org.'
            }
          />
        )}
      </div>
      <fieldset>
        <legend className="text-sm font-medium">Search languages</legend>
        <p className="mt-1 text-xs text-muted">
          Requested language coverage depends on the available sources.
        </p>
        <div className="mt-2 grid grid-cols-2 gap-x-4 sm:grid-cols-4">
          {languages.map(([code, label]) => (
            <label key={code} className="flex min-h-11 items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 accent-ember"
                checked={props.selectedLanguages.includes(code)}
                onChange={(event) =>
                  props.setLanguages(
                    event.target.checked
                      ? [...props.selectedLanguages, code]
                      : props.selectedLanguages.filter((item) => item !== code),
                  )
                }
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>
    </div>
  );
}
