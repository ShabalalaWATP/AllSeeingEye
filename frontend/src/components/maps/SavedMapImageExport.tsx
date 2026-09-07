import { useCallback, useRef, useState, useSyncExternalStore } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import type { SavedMapView } from '@/lib/api/mapViews';
import { fetchMapView } from '@/lib/api/mapViews';
import { fetchReport, type EvidenceItem } from '@/lib/api/reports';
import { fetchMapImagePackage, mapPngBase64, type MapImageUse } from '@/lib/api/mapImageExport';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { SelectField, TextAreaField } from '@/components/ui/Field';
import { MapImagePreview, type MapCapture } from './MapImagePreview';

export function SavedMapImageExport({ saved }: { saved: SavedMapView }) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return (
    <ExportBody key={`${actor}:${access}:${saved.view.id}:${saved.revision.id}`} saved={saved} />
  );
}
function ExportBody({ saved }: { saved: SavedMapView }) {
  const request = useScopedRequest();
  const [snapshot, setSnapshot] = useState<{
    saved: SavedMapView;
    evidence: EvidenceItem[];
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeAnnotations, setIncludeAnnotations] = useState(false);
  const [useBasis, setUseBasis] = useState<MapImageUse>('standard');
  const [permittedUse, setPermittedUse] = useState('');
  const capture = useRef<MapCapture | null>(null);
  const [ready, setReady] = useState(false);
  const onCaptureReady = useCallback((value: MapCapture | null) => {
    capture.current = value;
    setReady(value !== null);
  }, []);
  const close = () => {
    request(); // Cancels all previous work, including capture and pending API delivery.
    setSnapshot(null);
    setBusy(false);
    setError(null);
    capture.current = null;
    setReady(false);
  };
  const preview = async () => {
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const fresh = await fetchMapView(saved.view.id, saved.revision.id, signal);
      signal.throwIfAborted();
      if (
        fresh.view.id !== saved.view.id ||
        fresh.revision.id !== saved.revision.id ||
        fresh.view.report_id !== saved.view.report_id
      )
        throw new Error('The server returned a different saved map revision.');
      const report = await fetchReport(
        fresh.view.report_id,
        fresh.revision.report_version_number,
        signal,
      );
      signal.throwIfAborted();
      if (
        report.report.id !== fresh.view.report_id ||
        report.version.number !== fresh.revision.report_version_number
      )
        throw new Error('The report version does not match the saved map.');
      setUseBasis(
        fresh.revision.state.basemap.startsWith('os_')
          ? 'licensed'
          : ['satellite', 'hybrid'].includes(fresh.revision.state.basemap)
            ? 'noncommercial'
            : 'standard',
      );
      setSnapshot({ saved: fresh, evidence: report.version.evidence });
    } catch (failure) {
      if (!signal.aborted)
        setError(failure instanceof Error ? failure.message : 'Could not load the saved map.');
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const download = async () => {
    if (!snapshot || !capture.current) return;
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const png = await capture.current(signal);
      const encoded = await mapPngBase64(png, signal);
      signal.throwIfAborted();
      const zip = await fetchMapImagePackage(
        snapshot.saved.view.id,
        snapshot.saved.revision.id,
        {
          png_base64: encoded,
          include_annotations: includeAnnotations,
          use_basis: useBasis,
          permitted_use: permittedUse.trim(),
        },
        signal,
      );
      signal.throwIfAborted();
      saveBinaryFile(`map-revision-${snapshot.saved.revision.number}-image.zip`, zip);
    } catch (failure) {
      if (!signal.aborted)
        setError(failure instanceof Error ? failure.message : 'Could not export the map image.');
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const basemap = snapshot?.saved.revision.state.basemap ?? saved.revision.state.basemap;
  const os = basemap.startsWith('os_');
  const satellite = ['satellite', 'hybrid'].includes(basemap);
  const declarationRequired = includeAnnotations || os || satellite;
  return (
    <section aria-label="Saved map image export" className="space-y-3 border-t border-line pt-3">
      <h3 className="font-medium">Export saved map image</h3>
      <p className="text-xs text-muted">
        Create an image and provenance ZIP from saved revision {saved.revision.number}. Opening the
        preview fetches current basemap tiles from its configured provider and discloses the viewed
        area through those requests. Cartography may have changed since saving. The server checks
        access and revision metadata, but cannot attest that client-rendered pixels match the
        evidence.
      </p>
      {!snapshot && (
        <Button variant="secondary" busy={busy} onClick={() => void preview()}>
          Open saved image preview
        </Button>
      )}
      {snapshot && (
        <>
          <label className="flex gap-2 text-sm">
            <input
              type="checkbox"
              checked={includeAnnotations}
              disabled={busy}
              onChange={(event) => setIncludeAnnotations(event.target.checked)}
            />
            Include saved private overlays, research area and measurement
          </label>
          {(os || satellite) && (
            <SelectField
              label="Basemap reuse basis"
              value={useBasis}
              disabled={busy}
              onChange={(event) => setUseBasis(event.target.value as MapImageUse)}
              options={[
                ...(!os ? [{ value: 'noncommercial', label: 'Non-commercial use' }] : []),
                { value: 'licensed', label: 'I hold appropriate reuse rights' },
              ]}
            />
          )}
          {declarationRequired && (
            <TextAreaField
              label="Permitted use declaration"
              maxLength={1000}
              value={permittedUse}
              disabled={busy}
              hint="Describe your permitted reuse of this basemap and any included annotations. This is your declaration, not verification of permission."
              onChange={(event) => setPermittedUse(event.target.value)}
            />
          )}
          <MapImagePreview
            saved={snapshot.saved}
            evidence={snapshot.evidence}
            includeAnnotations={includeAnnotations}
            onCaptureReady={onCaptureReady}
          />
          <div className="flex gap-2">
            <Button
              busy={busy}
              disabled={!ready || (declarationRequired && !permittedUse.trim())}
              onClick={() => void download()}
            >
              Download map image ZIP
            </Button>
            <Button variant="ghost" onClick={close}>
              Close preview
            </Button>
          </div>
        </>
      )}
      {error && <Alert tone="error">{error}</Alert>}
    </section>
  );
}
