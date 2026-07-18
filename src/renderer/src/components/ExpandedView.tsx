import EyeShell from './EyeShell'
import TextAnalysis from './TextAnalysis'
import ScreenAnalysis from './ScreenAnalysis'
import VoiceAnalysis from './VoiceAnalysis'
import OverallReview from './OverallReview'
import ExpertInsight from './ExpertInsight'
import QuitButton from './QuitButton'
import { isBusy, useFitHeight, type GazeTarget } from '../hooks'
import {
  EXPERT_SHORT_LABELS,
  type CaptureSourceKind,
  type ExpertId,
  type StatePayload
} from '../../../shared/types'

export type ComposerTab = 'screen' | 'text' | 'voice'
export type PanelTab = ComposerTab | 'overall' | `expert:${ExpertId}`

interface ExpandedViewProps {
  snapshot: StatePayload
  cursor: GazeTarget
  tab: PanelTab
  requestedCaptureKind: CaptureSourceKind
  voiceActivation: number
  onTabChange: (tab: PanelTab) => void
}

export default function ExpandedView({
  snapshot,
  cursor,
  tab,
  requestedCaptureKind,
  voiceActivation,
  onTabChange
}: ExpandedViewProps): React.JSX.Element {
  const rootRef = useFitHeight<HTMLDivElement>()
  const report = snapshot.report
  const busy = isBusy(snapshot.state)
  const expertId = tab.startsWith('expert:') ? tab.slice(7) as ExpertId : null
  const analysis = expertId ? report?.expertAnalyses.find((item) => item.expertId === expertId) : undefined
  const contentTab: PanelTab = expertId && !analysis ? 'overall' : tab

  return (
    <div className="expanded-window panel" ref={rootRef}>
      <header className="expanded-header drag">
        <div className="header-eye no-drag">
          <EyeShell width={60} state={snapshot.state} cursor={cursor} interactive={false} />
        </div>
        <span className="title">AllSeeingEye</span>
        <nav className="composer-tabs no-drag" aria-label="Choose analysis input">
          <ComposerButton label="Visual" tab="screen" selected={contentTab === 'screen'} disabled={busy} onSelect={onTabChange} />
          <ComposerButton label="Text" tab="text" selected={contentTab === 'text'} disabled={busy} onSelect={onTabChange} />
          <ComposerButton label="Voice" tab="voice" selected={contentTab === 'voice'} disabled={busy} onSelect={onTabChange} />
        </nav>
        <button className="icon-btn no-drag" onClick={() => void window.criticalEye.collapse()} title="Collapse (Esc)">▾</button>
        <QuitButton />
      </header>

      {report && (
        <ResultTabBar snapshot={snapshot} selected={contentTab} onSelect={onTabChange} />
      )}

      <div
        className="expanded-content no-drag"
        role={contentTab === 'overall' || expertId ? 'tabpanel' : undefined}
        id="review-panel"
        tabIndex={contentTab === 'overall' || expertId ? 0 : undefined}
      >
        {contentTab === 'overall' && <OverallReview snapshot={snapshot} />}
        {contentTab === 'screen' && <ScreenAnalysis snapshot={snapshot} requestedKind={requestedCaptureKind} />}
        {contentTab === 'text' && <TextAnalysis snapshot={snapshot} />}
        {contentTab === 'voice' && (
          <VoiceAnalysis snapshot={snapshot} activationId={voiceActivation} />
        )}
        {analysis && (
          <ExpertInsight
            analysis={analysis}
            selection={report?.selectedExperts.find((item) => item.expertId === analysis.expertId)}
          />
        )}
      </div>

      <footer className="expanded-footer no-drag">
        <span className="privacy">Inputs are handled in memory and are not saved locally.</span>
        <button className="btn subtle" onClick={() => void window.criticalEye.togglePause()}>
          {snapshot.paused ? 'Resume' : 'Pause'}
        </button>
      </footer>
      <div className="shortcut-help no-drag">
        <kbd>Ctrl+Shift+R</kbd> quick display · <kbd>Ctrl+Shift+Space</kbd> show/hide · <kbd>Esc</kbd> collapse · <kbd>Alt+F4</kbd> quit
      </div>
    </div>
  )
}

function ComposerButton({
  label,
  tab,
  selected,
  disabled,
  onSelect
}: {
  label: string
  tab: ComposerTab
  selected: boolean
  disabled: boolean
  onSelect: (tab: PanelTab) => void
}): React.JSX.Element {
  return <button className={selected ? 'active' : ''} aria-pressed={selected} disabled={disabled} onClick={() => onSelect(tab)}>{label}</button>
}

function ResultTabBar({
  snapshot,
  selected,
  onSelect
}: {
  snapshot: StatePayload
  selected: PanelTab
  onSelect: (tab: PanelTab) => void
}): React.JSX.Element {
  const items: Array<{ tab: PanelTab; label: string; title: string }> = [
    { tab: 'overall', label: 'Overall', title: 'Overall review' },
    ...(snapshot.report?.expertAnalyses.map((analysis) => ({
      tab: `expert:${analysis.expertId}` as PanelTab,
      label: EXPERT_SHORT_LABELS[analysis.expertId],
      title: EXPERT_SHORT_LABELS[analysis.expertId]
    })) ?? [])
  ]
  const activeIndex = Math.max(0, items.findIndex((item) => item.tab === selected))
  const move = (index: number): void => {
    const bounded = (index + items.length) % items.length
    onSelect(items[bounded].tab)
    requestAnimationFrame(() => {
      document.getElementById(`result-tab-${bounded}`)?.focus()
    })
  }

  return (
    <nav className="result-tabs no-drag" role="tablist" aria-label="Review results">
      {items.map((item, index) => (
        <button
          id={`result-tab-${index}`}
          key={item.tab}
          className={index === activeIndex ? 'active' : ''}
          role="tab"
          aria-selected={index === activeIndex}
          aria-controls="review-panel"
          tabIndex={index === activeIndex ? 0 : -1}
          title={item.title}
          onClick={() => onSelect(item.tab)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowRight') { event.preventDefault(); move(index + 1) }
            if (event.key === 'ArrowLeft') { event.preventDefault(); move(index - 1) }
            if (event.key === 'Home') { event.preventDefault(); move(0) }
            if (event.key === 'End') { event.preventDefault(); move(items.length - 1) }
          }}
        >
          {item.label}
        </button>
      ))}
    </nav>
  )
}
