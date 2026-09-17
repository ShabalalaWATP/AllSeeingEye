import { Link, useSearchParams } from 'react-router';

import { useAuthStore } from '@/stores/auth';

import { AiUsageSummary } from './AiUsageSummary';
import { AppearancePreferences } from './AppearancePreferences';
import { ProfilePreferences } from './ProfilePreferences';

const sections = [
  { id: 'appearance', label: 'Appearance' },
  { id: 'region', label: 'Time & region' },
  { id: 'research', label: 'Research defaults' },
  { id: 'reports', label: 'Report preferences' },
  { id: 'ai-usage', label: 'AI allowance' },
] as const;

const resources = [
  {
    to: '/warning',
    title: 'Alerts & rules',
    detail: 'Review your alerts and manage the activity rules that create them.',
  },
  {
    to: '/account?section=security',
    title: 'Account security',
    detail: 'Manage multi-factor authentication, passwords and active sessions.',
  },
];

export default function SettingsPage() {
  const actor = useAuthStore((state) => state.user);
  const [params] = useSearchParams();
  const selected = sections.find((section) => section.id === params.get('section')) ?? sections[0];
  if (!actor) return null;
  return (
    <section className="h-full overflow-y-auto p-4 sm:p-8">
      <div className="mx-auto max-w-6xl">
        <header className="border-b border-line pb-7">
          <p className="font-mono text-xs uppercase tracking-widest text-muted">
            Personal workspace
          </p>
          <h1 className="mt-2 text-3xl font-semibold">Settings</h1>
          <p className="mt-2 text-sm text-muted">
            Set up the app for the way you work. These preferences apply only to you.
          </p>
        </header>
        <div className="grid gap-8 py-7 md:grid-cols-[190px_minmax(0,1fr)] md:gap-12">
          <nav
            aria-label="Personal settings"
            className="flex gap-1 overflow-x-auto md:flex-col md:self-start"
          >
            {sections.map((section) => (
              <Link
                key={section.id}
                to={`?section=${section.id}`}
                aria-current={selected.id === section.id ? 'page' : undefined}
                className={`min-h-11 shrink-0 rounded-md px-3 py-3 text-sm transition-colors ${selected.id === section.id ? 'bg-surface-2 text-ember' : 'text-muted hover:bg-surface-2 hover:text-text'}`}
              >
                {section.label}
              </Link>
            ))}
            <Link
              to="/account"
              className="min-h-11 shrink-0 rounded-md px-3 py-3 text-sm text-muted hover:text-text md:mt-5"
            >
              Profile & teams
            </Link>
          </nav>
          <div key={`${actor.id}:${selected.id}`} className="min-w-0 max-w-3xl">
            {selected.id === 'ai-usage' ? (
              <AiUsageSummary />
            ) : selected.id === 'appearance' ? (
              <AppearancePreferences />
            ) : (
              <ProfilePreferences section={selected.id} />
            )}
            <section aria-label="Workspace resources" className="mt-12 border-t border-line pt-6">
              <h2 className="text-sm font-semibold">Workspace resources</h2>
              <div className="mt-3 divide-y divide-line">
                {resources.map((resource) => (
                  <Link
                    key={resource.to}
                    to={resource.to}
                    className="group flex items-center justify-between gap-4 py-4"
                  >
                    <span>
                      <span className="block text-sm font-medium group-hover:text-ember">
                        {resource.title}
                      </span>
                      <span className="mt-1 block text-xs text-muted">{resource.detail}</span>
                    </span>
                    <span aria-hidden="true" className="text-muted group-hover:text-ember">
                      ↗
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </section>
  );
}
