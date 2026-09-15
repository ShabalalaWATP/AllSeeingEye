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
        aria-label={open ? 'Minimise Eye assistant' : 'Open Eye assistant'}
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
        {chat.busy && (
          <span className="eye-launcher-working" role="status" aria-label="Answer in progress" />
        )}
        {unread && <span className="eye-launcher-ready" role="status" aria-label="Answer ready" />}
      </button>
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
