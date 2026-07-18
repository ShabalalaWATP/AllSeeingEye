import EyeShell from './EyeShell'
import { statusText, useElapsed, type GazeTarget } from '../hooks'
import type { StatePayload } from '../../../shared/types'

interface EyeWindowProps {
  snapshot: StatePayload
  cursor: GazeTarget
}

/** The 200x150 idle window: just the eye and a whisper of status. */
export default function EyeWindow({ snapshot, cursor }: EyeWindowProps): React.JSX.Element {
  const elapsed = useElapsed(snapshot.state === 'analysing')
  return (
    <div className="eye-window">
      <EyeShell
        width={200}
        state={snapshot.state}
        severity={snapshot.finding?.severity ?? null}
        cursor={cursor}
      />
      <div className="status-label drag">{statusText(snapshot.state, elapsed)}</div>
    </div>
  )
}
