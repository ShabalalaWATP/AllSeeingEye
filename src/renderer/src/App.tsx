import { useEffect, useRef, useState } from 'react'
import { useCompanion, useCursorTarget } from './hooks'
import EyeWindow, { type LauncherAction } from './components/EyeWindow'
import CompactView from './components/CompactView'
import ExpandedView, { type PanelTab } from './components/ExpandedView'
import type { CaptureSourceKind } from '../../shared/types'

export default function App(): React.JSX.Element {
  const snapshot = useCompanion()
  const cursor = useCursorTarget()
  const [tab, setTab] = useState<PanelTab>('screen')
  const [requestedCaptureKind, setRequestedCaptureKind] = useState<CaptureSourceKind>('display')
  const [launcherRequest, setLauncherRequest] = useState(0)
  const [voiceActivation, setVoiceActivation] = useState(0)
  const lastOpenedRun = useRef<string | null>(null)

  const openInput = (action: LauncherAction): void => {
    if (action === 'screen' || action === 'window') {
      setRequestedCaptureKind(action === 'screen' ? 'display' : 'window')
      setTab('screen')
    } else {
      setTab(action)
      if (action === 'voice') setVoiceActivation((value) => value + 1)
    }
    void window.criticalEye.setWindowMode('expanded')
  }

  useEffect(
    () => window.criticalEye.onUi((payload) => {
      if (payload.action === 'open-launcher') {
        setLauncherRequest((request) => request + 1)
      }
      if (payload.action === 'open-text') setTab('text')
      if (payload.action === 'open-voice') {
        setTab('voice')
        setVoiceActivation((value) => value + 1)
      }
      if (payload.action === 'open-screen' || payload.action === 'open-window') {
        setRequestedCaptureKind(payload.action === 'open-window' ? 'window' : 'display')
        setTab('screen')
      }
    }),
    []
  )

  useEffect(() => {
    const runId = snapshot.report?.runId
    if (runId && runId !== lastOpenedRun.current) {
      lastOpenedRun.current = runId
      setTab('overall')
      requestAnimationFrame(() => {
        requestAnimationFrame(() => document.getElementById('result-tab-0')?.focus())
      })
    }
  }, [snapshot.report?.runId])

  const changeTab = (next: PanelTab): void => {
    if (next === 'voice' && tab !== 'voice') {
      setVoiceActivation((value) => value + 1)
    }
    setTab(next)
  }

  const openFullReview = (): void => {
    setTab('overall')
    if (snapshot.report) {
      void window.criticalEye.setWindowMode('expanded')
      return
    }
    if (snapshot.quickResult && snapshot.canRunFullReview) {
      void window.criticalEye.runFullReview(snapshot.quickResult.runId)
    }
  }

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape' && snapshot.windowMode === 'expanded') {
        void window.criticalEye.collapse()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [snapshot.windowMode])

  if (snapshot.windowMode === 'eye') {
    return (
      <EyeWindow
        snapshot={snapshot}
        cursor={cursor}
        launcherRequest={launcherRequest}
        onChoose={openInput}
      />
    )
  }
  if (snapshot.windowMode === 'compact') {
    return <CompactView snapshot={snapshot} cursor={cursor} onFullReview={openFullReview} />
  }
  return (
    <ExpandedView
      snapshot={snapshot}
      cursor={cursor}
      tab={tab}
      requestedCaptureKind={requestedCaptureKind}
      voiceActivation={voiceActivation}
      onTabChange={changeTab}
    />
  )
}
