import { Component } from 'react';
import type { ReactNode } from 'react';

interface BoundaryState {
  failed: boolean;
}

/** A failed assistant must never replace or reload the surrounding map workspace. */
export class AssistantBoundary extends Component<{ children: ReactNode }, BoundaryState> {
  override state: BoundaryState = { failed: false };

  static getDerivedStateFromError(): BoundaryState {
    return { failed: true };
  }

  override render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="eye-assistant">
        <button
          type="button"
          className="eye-restart"
          onClick={() => this.setState({ failed: false })}
        >
          <img src="/brand/eye-512.png" alt="" aria-hidden="true" width="64" height="42" />
          <span>
            Restart Eye assistant
            <small>Clear this chat and try again.</small>
          </span>
        </button>
      </div>
    );
  }
}
