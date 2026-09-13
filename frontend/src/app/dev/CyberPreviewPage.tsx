/**
 * Development-only page (registered when import.meta.env.DEV) that renders the
 * cyber workspace sections and the authenticated shell chrome from test fixtures,
 * so the layout can be inspected in a browser without an account or live feeds.
 * Nothing here talks to the API; the fixtures are the same ones the tests use.
 */
import { useState } from 'react';

import { LeftRail } from '@/app/shell/LeftRail';
import { TopBar } from '@/app/shell/TopBar';
import { CyberActivity } from '@/features/cyber/CyberActivity';
import { CyberActors } from '@/features/cyber/CyberActors';
import { CyberAssessment } from '@/features/cyber/CyberAssessment';
import { CyberCharts } from '@/features/cyber/CyberCharts';
import { CyberFocusAreas } from '@/features/cyber/CyberFocusAreas';
import { CyberGnss } from '@/features/cyber/CyberGnss';
import { CyberHeader } from '@/features/cyber/CyberHeader';
import { CyberKpis } from '@/features/cyber/CyberKpis';
import { CyberNationState } from '@/features/cyber/CyberNationState';
import { CyberSectionNav, SectionHeading } from '@/features/cyber/CyberSectionNav';
import { CyberSourceCoverage } from '@/features/cyber/CyberSourceCoverage';
import { CyberVulnerabilities } from '@/features/cyber/CyberVulnerabilities';
import type { CyberDays } from '@/lib/api/cyber';
import { report } from '@/test/fixtures';
import { cyberActors, cyberBriefing, cyberSnapshot } from '@/test/fixtures.cyber';
import { jamMap } from '@/test/fixtures.trackers';

const noop = () => undefined;

export default function CyberPreviewPage() {
  const [days, setDays] = useState<CyberDays>(7);
  const [selectedActor, setSelectedActor] = useState('G0016');
  const data = cyberSnapshot(days);
  const briefing = cyberBriefing(days);
  briefing.job.status = 'completed';
  briefing.job.report_id = report.report.id;
  const briefingState = {
    briefing,
    report,
    error: null,
    loading: false,
    retry: noop,
  };
  const gnss = { data: jamMap, error: null, loading: false, reload: () => Promise.resolve() };
  return (
    <div className="flex h-dvh w-full overflow-hidden bg-ground text-text">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="relative min-h-0 flex-1">
          <section className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10">
            <div className="mx-auto max-w-[1500px] space-y-8 pb-28">
              <CyberHeader
                days={days}
                onDays={setDays}
                data={data}
                loading={false}
                onRefresh={noop}
                onOpenMap={noop}
              />
              <CyberSectionNav preparing={false} />
              <section id="cyber-overview" className="space-y-5">
                <SectionHeading
                  id="cyber-overview"
                  eyebrow="Overview"
                  title="The current picture"
                />
                <CyberKpis data={data} />
                <CyberCharts data={data} onCountry={noop} />
              </section>
              <section id="cyber-assessment" className="space-y-5">
                <SectionHeading id="cyber-assessment" eyebrow="Assessment" title="AI assessment" />
                <CyberAssessment state={briefingState} days={days} />
              </section>
              <section id="cyber-focus" className="space-y-5">
                <SectionHeading id="cyber-focus" eyebrow="Focus areas" title="Themed lenses" />
                <CyberFocusAreas data={data} report={report} onTheme={noop} />
              </section>
              <section id="cyber-nation-state" className="space-y-5">
                <SectionHeading
                  id="cyber-nation-state"
                  eyebrow="Nation-state"
                  title="State mentions"
                />
                <CyberNationState
                  data={data}
                  actors={cyberActors.catalogue?.actors ?? []}
                  actorStatus="ready"
                  onActor={setSelectedActor}
                />
              </section>
              <section id="cyber-gnss" className="space-y-5">
                <SectionHeading id="cyber-gnss" eyebrow="GNSS" title="GPS and GNSS interference" />
                <CyberGnss gnss={gnss} items={[]} onOpenMap={noop} />
              </section>
              <section id="cyber-vulnerabilities" className="space-y-5">
                <SectionHeading id="cyber-vulnerabilities" eyebrow="Exploitation" title="KEV" />
                <CyberVulnerabilities items={data.items} />
              </section>
              <section id="cyber-actors" className="space-y-5">
                <SectionHeading id="cyber-actors" eyebrow="Reference" title="Threat actors" />
                <CyberActors
                  data={cyberActors}
                  items={data.items}
                  mentions={data.actor_mentions}
                  activityStatus="ready"
                  selectedId={selectedActor}
                  onSelect={setSelectedActor}
                  onActivity={noop}
                />
              </section>
              <section id="cyber-activity" className="space-y-5">
                <SectionHeading
                  id="cyber-activity"
                  eyebrow="Activity"
                  title="Collected reporting"
                />
                <CyberActivity items={data.items} days={days} onActor={noop} onTheme={noop} />
              </section>
              <section id="cyber-sources" className="space-y-5">
                <SectionHeading id="cyber-sources" eyebrow="Sources" title="Coverage" />
                <CyberSourceCoverage data={data} />
              </section>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
