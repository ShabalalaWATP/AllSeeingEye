import { useEffect, useState } from 'react'
import { useCompanion, useCursorTarget } from './hooks'
import EyeWindow from './components/EyeWindow'
import CompactView from './components/CompactView'
import ExpandedView, { type PanelTab } from './components/ExpandedView'

export default function App(): React.JSX.Element {
  const snapshot = useCompanion()
  const cursor = useCursorTarget()
  const [tab, setTab] = useState<PanelTab>('finding')

  // The context menu can ask for the text tab directly.
  useEffect(
    () =>
      window.criticalEye.onUi((payload) => {
        if (payload.action === 'open-text') setTab('text')
      }),
    []
  )

  // A fresh finding pulls the expanded panel back to the finding tab.
  useEffect(() => {
    if (snapshot.finding) setTab('finding')
  }, [snapshot.finding])

  // Escape collapses the expanded panel (renderer-local, never a global shortcut).
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape' && snapshot.windowMode === 'expanded') {
        void window.criticalEye.collapse()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [snapshot.windowMode])

  if (snapshot.windowMode === 'eye') return <EyeWindow snapshot={snapshot} cursor={cursor} />
  if (snapshot.windowMode === 'compact') return <CompactView snapshot={snapshot} cursor={cursor} />
  return <ExpandedView snapshot={snapshot} cursor={cursor} tab={tab} onTabChange={setTab} />
}
