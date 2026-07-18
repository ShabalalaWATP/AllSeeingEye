import EyeShell from './EyeShell'
import FindingDetail from './FindingDetail'
import TextAnalysis from './TextAnalysis'
import type { GazeTarget } from '../hooks'
import type { StatePayload } from '../../../shared/types'

export type PanelTab = 'finding' | 'text'

interface ExpandedViewProps {
  snapshot: StatePayload
  cursor: GazeTarget
  tab: PanelTab
  onTabChange: (tab: PanelTab) => void
}

/** The 560x620 window: full detail, mode selection and manual text analysis. */
export default function ExpandedView({
  snapshot,
  cursor,
  tab,
  onTabChange
}: ExpandedViewProps): React.JSX.Element {
  return (
    <div className="expanded-window panel">
      <header className="expanded-header drag">
        <div className="header-eye no-drag">
          <EyeShell size={44} state={snapshot.state} cursor={cursor} interactive={false} />
        </div>
        <span className="title">Critical Eye</span>
        <nav className="tabs no-drag">
          <button
            className={`tab ${tab === 'finding' ? 'active' : ''}`}
            onClick={() => onTabChange('finding')}
          >
            Finding
          </button>
          <button
            className={`tab ${tab === 'text' ? 'active' : ''}`}
            onClick={() => onTabChange('text')}
          >
            Text
          </button>
        </nav>
        <button
          className="icon-btn no-drag"
          onClick={() => void window.criticalEye.collapse()}
          title="Collapse (Esc)"
        >
          ▾
        </button>
        <button
          className="icon-btn no-drag"
          onClick={() => void window.criticalEye.dismiss()}
          title="Close"
        >
          ✕
        </button>
      </header>

      <div className="expanded-content no-drag">
        {tab === 'finding' ? <FindingDetail snapshot={snapshot} /> : (
          <TextAnalysis snapshot={snapshot} />
        )}
      </div>

      <footer className="expanded-footer no-drag">
        <span className="privacy">Screenshots are analysed in memory and are not saved.</span>
        <button className="btn subtle" onClick={() => void window.criticalEye.togglePause()}>
          {snapshot.paused ? 'Resume' : 'Pause'}
        </button>
      </footer>
      <div className="shortcut-help no-drag">
        <kbd>Ctrl+Shift+R</kbd> analyse · <kbd>Ctrl+Shift+Space</kbd> show/hide ·{' '}
        <kbd>Ctrl+Alt+P</kbd> pause · <kbd>Esc</kbd> collapse
      </div>
    </div>
  )
}
