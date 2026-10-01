import { useEffect, useId, useRef, useState, useSyncExternalStore } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { clearAssistantMapFocus } from '@/lib/assistantMapContext';
import { useAssistantReportContext } from '@/lib/assistantReportContext';
import { AssistantEye } from '@/components/brand/AssistantEye';
import { LAUNCHER_HEIGHT, LAUNCHER_WIDTH, useAssistantPosition } from './useAssistantPosition';
import { panelPlacement } from './panelPlacement';
import { useEyeChat } from './useEyeChat';
import { EyeAssistantPanel } from './EyeAssistantPanel';
import { AssistantBoundary } from './AssistantBoundary';
import { useEyeStatus } from './eyeStatus';
import './eyeAssistant.css';
import './eyeLauncher.css';

function EyeSession() {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [seenTurn, setSeenTurn] = useState<number | null>(null);
  const placement = useAssistantPosition();
  const chat = useEyeChat();
  const reportContext = useAssistantReportContext();
  const seenReportLaunch = useRef(reportContext.launch?.token ?? 0);
  const launcher = useRef<HTMLButtonElement>(null);
  const panelId = useId(),
    helpId = useId();
  const close = () => {
    const last = chat.turns.at(-1);
    if (last?.status === 'answered') setSeenTurn(last.id);
    setOpen(false);
    launcher.current?.focus();
  };
  const latest = chat.turns.at(-1);
  const status = useEyeStatus(chat.turns);
  const unread = !open && latest?.status === 'answered' && latest.id !== seenTurn;
  useEffect(() => () => clearAssistantMapFocus(), []);
  useEffect(() => {
    const launch = reportContext.launch;
    if (!launch || launch.token <= seenReportLaunch.current) return;
    seenReportLaunch.current = launch.token;
    chat.beginReport(launch.report);
    setSeenTurn(null);
    setOpen(true);
  }, [reportContext.launch, chat]);
  return (
    <div className="eye-assistant" data-dragging={placement.dragging}>
      <button
        ref={launcher}
        type="button"
        className="eye-launcher"
        // The name matches the visible "ASK EYE" text; aria-expanded carries open or minimised.
        aria-label="Ask Eye"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-describedby={helpId}
        style={{
          left: placement.position.x,
          top: placement.position.y,
          width: LAUNCHER_WIDTH,
          height: LAUNCHER_HEIGHT,
        }}
        onPointerDown={placement.onPointerDown}
        onPointerMove={placement.onPointerMove}
        onPointerUp={placement.onPointerUp}
        onPointerCancel={placement.onPointerCancel}
        onKeyDown={placement.onKeyDown}
        onClick={() => {
          if (placement.allowClick()) {
            if (open) close();
            else {
              if (latest?.status === 'answered') setSeenTurn(latest.id);
              setOpen(true);
            }
          }
        }}
      >
        <AssistantEye className="eye-launcher-mark" />
        <span className="eye-launcher-label" aria-hidden="true">
          ASK EYE
        </span>
        {/* Visual cues only: the status region below carries the same states as text. */}
        {chat.busy && <span className="eye-launcher-working" aria-hidden="true" />}
        {unread && <span className="eye-launcher-ready" aria-hidden="true" />}
      </button>
      {/* A polite live region without the status role, so pages keep their own single status. */}
      <p aria-live="polite" aria-atomic="true" className="sr-only" data-eye-status="">
        {status}
      </p>
      <span id={helpId} className="sr-only">
        Click to chat. Drag to move. Arrow keys reposition; Home resets. Hold Shift for larger
        steps.
      </span>
      {placement.announcement && (
        <span role="status" className="sr-only">
          {placement.announcement}
        </span>
      )}
      {open && (
        <EyeAssistantPanel
          id={panelId}
          chat={chat}
          onClose={close}
          onResetPosition={placement.reset}
          expanded={expanded}
          onToggleExpanded={() => setExpanded((previous) => !previous)}
          style={panelPlacement(placement.position, expanded)}
        />
      )}
    </div>
  );
}

/** Authentication and access changes replace the entire ephemeral conversation immediately. */
export function EyeAssistant() {
  const actor = useAuthStore((state) =>
    state.status === 'authenticated' && state.user?.is_active
      ? `${state.user.id}:${state.user.role}`
      : null,
  );
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return actor ? (
    <AssistantBoundary key={`${actor}:${revision}`}>
      <EyeSession />
    </AssistantBoundary>
  ) : null;
}
