import { useEffect, useId, useRef, useState, useSyncExternalStore } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { clearAssistantMapFocus } from '@/lib/assistantMapContext';
import { useAssistantPosition } from './useAssistantPosition';
import { useEyeChat } from './useEyeChat';
import { EyeAssistantPanel } from './EyeAssistantPanel';
import { AssistantBoundary } from './AssistantBoundary';
import './eyeAssistant.css';

function EyeSession() {
  const [open, setOpen] = useState(false);
  const placement = useAssistantPosition();
  const chat = useEyeChat();
  const launcher = useRef<HTMLButtonElement>(null);
  const panelId = useId(),
    helpId = useId();
  const close = () => {
    chat.stop();
    setOpen(false);
    launcher.current?.focus();
  };
  useEffect(() => () => clearAssistantMapFocus(), []);
  const width = Math.min(390, window.innerWidth - 24);
  const height = Math.min(600, window.innerHeight - 32);
  const panelStyle = {
    left: Math.max(12, Math.min(window.innerWidth - width - 12, placement.position.x + 76 - width)),
    top: Math.max(
      16,
      Math.min(window.innerHeight - height - 16, placement.position.y - height - 10),
    ),
    width,
    maxHeight: height,
  };
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
        style={{ left: placement.position.x, top: placement.position.y }}
        onPointerDown={placement.onPointerDown}
        onPointerMove={placement.onPointerMove}
        onPointerUp={placement.onPointerUp}
        onPointerCancel={placement.onPointerCancel}
        onKeyDown={placement.onKeyDown}
        onClick={() => {
          if (placement.allowClick()) {
            if (open) close();
            else setOpen(true);
          }
        }}
      >
        <img
          src="/brand/eye-512.png"
          alt=""
          aria-hidden="true"
          draggable={false}
          width="64"
          height="42"
        />
        <span aria-hidden="true">ASK EYE</span>
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
          style={panelStyle}
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
