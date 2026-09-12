import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { PhotoGeolocationPanel } from './PhotoGeolocationPanel';

export default function PhotoResearchPage() {
  const workspaces = useWorkspaces();
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl space-y-7">
        <header>
          <h1 className="text-3xl font-semibold tracking-tight">Geolocation</h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
            Compare photographs, examine visible clues and assess possible locations. Save the
            findings with supporting evidence and the checks still needed.
          </p>
        </header>
        <PhotoGeolocationPanel key={workspaces.key} workspaces={workspaces} />
      </div>
    </section>
  );
}
