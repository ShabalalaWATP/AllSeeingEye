/**
 * Holds a jump-link target's place while its data loads or after it fails, so in-page
 * navigation always lands somewhere and says why the section is empty.
 */
export function SectionPendingNote({ loading, subject }: { loading: boolean; subject: string }) {
  return (
    <p className="rounded-md border border-dashed border-line px-3 py-4 text-sm text-muted">
      {loading
        ? `Waiting for ${subject} to load.`
        : `Not available: ${subject} could not be loaded.`}
    </p>
  );
}

/** A titled placeholder section for pages whose sections own their own ids and headings. */
export function PendingSection({
  id,
  title,
  loading,
  subject,
}: {
  id: string;
  title: string;
  loading: boolean;
  subject: string;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-pending-heading`} className="flex flex-col gap-3">
      <h2 id={`${id}-pending-heading`} className="text-base font-semibold">
        {title}
      </h2>
      <SectionPendingNote loading={loading} subject={subject} />
    </section>
  );
}
