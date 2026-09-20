import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';

import { EventRow } from '@/components/events/EventRow';
import { BackToTrackers } from './TrackerParts';
import { describeSocialActivity, useSocialBoard } from './useSocialBoard';

export default function SocialPage() {
  const { data, error, loading, reload, showOnGlobe } = useSocialBoard();
  return (
    <article className="flex h-full flex-col gap-5 overflow-y-auto p-6">
      <header className="flex flex-col gap-2">
        <BackToTrackers />
        <h1 className="text-xl font-semibold">Social listening</h1>
        <p className="text-sm text-muted">
          Public posts and outlet videos retained from the last 24 hours. Counts describe the
          watched feeds, not platform-wide activity or verification of a claim.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              void reload();
            }}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button variant="secondary" onClick={showOnGlobe}>
            Show social layer on globe
          </Button>
        </div>
      </header>
      {error !== null && <Alert tone="error">{describeError(error)}</Alert>}
      {loading && <LoadingNote label="Loading social listening" />}
      {data !== null && (
        <>
          <p className="font-mono text-sm text-muted">
            {data.total} posts · {data.located} with a location · as of {formatUtc(data.window_end)}
          </p>
          <section aria-label="Platforms and instances" className="flex flex-col gap-2">
            <h2 className="text-base font-semibold">Platforms and instances</h2>
            {data.platforms.length === 0 ? (
              <p className="text-sm text-muted">No social posts in the retained day.</p>
            ) : (
              <Table caption="Posts by platform and instance">
                <thead>
                  <tr>
                    <Th>Platform</Th>
                    <Th>Instance</Th>
                    <Th>Posts</Th>
                    <Th>Located</Th>
                  </tr>
                </thead>
                <tbody>
                  {data.platforms.map((row) => (
                    <tr key={`${row.platform}/${row.instance}`}>
                      <Td>{row.platform}</Td>
                      <Td>{row.instance}</Td>
                      <Td>{row.count}</Td>
                      <Td>{row.located}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </section>
          <section aria-label="Top hashtags" className="flex flex-col gap-2">
            <h2 className="text-base font-semibold">Top hashtags in the last 24 hours</h2>
            {data.hashtags.length === 0 ? (
              <p className="text-sm text-muted">No hashtags in retained posts.</p>
            ) : (
              <ul className="flex flex-wrap gap-3">
                {data.hashtags.map((row) => (
                  <li key={row.tag} className="text-sm">
                    #{row.tag} <span className="font-mono text-muted">{row.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section aria-label="Keyword activity" className="flex flex-col gap-2">
            <h2 className="text-base font-semibold">Keyword activity</h2>
            <p className="text-sm text-muted">
              Complete hour starting {formatUtc(data.keyword_hour)}, against sampled hours from the
              previous 30 days. A burst needs at least six baseline hours, three posts and twice the
              mean. Watchlist terms and your enabled collection terms are sampled, up to 32 terms
              across the instance.
            </p>
            {data.keywords.length === 0 ? (
              <p className="text-sm text-muted">No configured keywords are being sampled.</p>
            ) : (
              <Table caption="Keyword activity against hourly baselines">
                <thead>
                  <tr>
                    <Th>Keyword</Th>
                    <Th>Posts</Th>
                    <Th>Hourly mean</Th>
                    <Th>Signal</Th>
                  </tr>
                </thead>
                <tbody>
                  {data.keywords.map((row) => (
                    <tr key={row.term}>
                      <Td>{row.term}</Td>
                      <Td>{row.count}</Td>
                      <Td>{row.baseline === null ? 'Pending' : row.baseline.toFixed(1)}</Td>
                      <Td className={row.burst ? 'text-critical' : 'text-muted'}>
                        {describeSocialActivity(row)}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </section>
          <section aria-label="Latest posts" className="flex flex-col gap-2">
            <h2 className="text-base font-semibold">Latest posts</h2>
            {data.posts.length === 0 ? (
              <p className="text-sm text-muted">No recent posts to display.</p>
            ) : (
              <ul>
                {data.posts.map((event) => (
                  <EventRow key={event.id} event={event} />
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </article>
  );
}
