import { useState } from 'react';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { AdminPage } from '@/components/admin/AdminPage';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/auth';

import { PeopleCard, RequestsCard, SecurityCard } from './overview/AccessCards';
import { AuditCard } from './overview/AuditCard';
import { ConnectionsCard, SourcesCard, UsageCard } from './overview/ServiceCards';

/** Each tile loads its own bounded data, so one failing service never hides the others. */
export default function AdminOverviewPage() {
  const name = useAuthStore((state) => state.user?.display_name);
  const [round, setRound] = useState(0);
  return (
    <AdminPage
      eyebrow="Operations console"
      title="Administration"
      width="wide"
      description={
        <p className="max-w-2xl">
          Manage access, configure the services used by researchers and review administrative
          activity. Changes here can affect people across the application.
        </p>
      }
      meta={
        name === undefined ? undefined : (
          <p className="text-xs text-muted">
            Signed in as <span className="font-medium text-text">{name}</span>
          </p>
        )
      }
      actions={
        <Button variant="secondary" onClick={() => setRound((value) => value + 1)}>
          <AdminIcon name="refresh" size={16} />
          Refresh overview
        </Button>
      }
    >
      <div
        key={round}
        className="grid grid-flow-row-dense grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
      >
        <RequestsCard />
        <PeopleCard />
        <SecurityCard />
        <SourcesCard className="md:col-span-2" />
        <ConnectionsCard />
        <AuditCard className="md:col-span-2 xl:col-span-2" />
        <UsageCard />
      </div>
    </AdminPage>
  );
}
