import { randomUUID } from 'node:crypto'
import { app } from 'electron'
import { AnalysisGate } from './core/gate'
import { canTrigger, displayState } from './core/state'
import { toUserError } from './core/error-map'
import { MissingKeyError } from './core/errors'
import { AnalysisSession } from './core/analysis-session'
import type { PendingReviewInput } from './core/pending-review'
import { captureTarget } from './capture'
import { getModel, hasApiKey, transcribeVoice as requestTranscription } from './openai-client'
import { runQuickAnalysis } from './quick-analysis'
import { runExpertBoard } from './agents/orchestrator'
import { primaryFinding } from './agents/schemas'
import type { WindowManager } from './window'
import type { PrefsStore } from './prefs'
import type {
  AnalysisMode,
  AnalysisReport,
  AnalysisSource,
  CaptureTarget,
  CompanionState,
  QuickResult,
  RedTeamFinding,
  ReviewDepth,
  ReviewPhase,
  StatePayload,
  UserError,
  VoiceMimeType,
  WindowMode
} from '../shared/types'

/**
 * Owns the companion state machine and the single-use hand-off from a quick
 * take to a full expert review. Input references never leave this process.
 */
export class AnalysisController {
  private state: CompanionState = 'idle'
  private paused: boolean
  private finding: RedTeamFinding | null = null
  private quickResult: QuickResult | null = null
  private report: AnalysisReport | null = null
  private error: UserError | null = null
  private reviewPhase: ReviewPhase | null = null
  private readonly gate = new AnalysisGate()
  private readonly session: AnalysisSession
  private voiceSessionId: string | null = null

  constructor(
    private wm: WindowManager,
    private prefs: PrefsStore
  ) {
    this.paused = prefs.get().startPaused
    this.session = new AnalysisSession(() => this.push())
  }

  get isPaused(): boolean {
    return this.paused
  }

  snapshot(): StatePayload {
    const p = this.prefs.get()
    const canRunFullReview = Boolean(
      this.quickResult &&
      !this.paused &&
      !this.gate.isBusy &&
      this.session.hasPending(this.quickResult.runId)
    )
    return {
      state: displayState(this.state, this.paused),
      windowMode: this.wm.mode,
      analysisMode: p.mode,
      reviewDepth: p.reviewDepth,
      paused: this.paused,
      privacyNoticeDismissed: p.privacyNoticeDismissed,
      finding: this.finding,
      quickResult: this.quickResult,
      report: this.report,
      error: this.error,
      reviewPhase: this.reviewPhase,
      canRunFullReview
    }
  }

  push(): void {
    if (this.wm.win.isDestroyed()) return
    this.wm.win.webContents.send('state', this.snapshot())
  }

  async runScreen(
    focusQuestion = '',
    depth?: ReviewDepth,
    target: CaptureTarget = { type: 'display-under-pointer' }
  ): Promise<void> {
    if (!canTrigger(this.paused, this.gate.isBusy) || !this.gate.tryAcquire()) {
      this.push()
      return
    }
    const generation = this.beginQuickRun()
    const abortController = this.session.startAbortableOperation()
    let dataUrl: string | null = null
    try {
      if (!hasApiKey()) throw new MissingKeyError()
      this.setState('capturing')
      dataUrl = await captureTarget(this.wm.win, target)
      if (!this.session.isCurrent(generation)) return
      if (depth) this.prefs.set({ reviewDepth: depth })
      this.setState('analysing')
      const answer = await runQuickAnalysis(
        'screen', dataUrl, focusQuestion.trim(), abortController.signal
      )
      if (!this.session.isCurrent(generation)) return
      this.finishQuick(answer, {
        runId: randomUUID(),
        source: 'screen',
        artefact: dataUrl,
        focusQuestion: focusQuestion.trim()
      })
    } catch (err) {
      if (this.session.isCurrent(generation)) this.failQuick(err)
    } finally {
      dataUrl = null
      this.session.finishAbortableOperation(abortController)
      this.gate.release()
      this.push()
    }
  }

  async runText(
    text: string,
    mode: AnalysisMode,
    focusQuestion = '',
    depth?: ReviewDepth,
    source: AnalysisSource = 'text'
  ): Promise<void> {
    if (!canTrigger(this.paused, this.gate.isBusy) || !this.gate.tryAcquire()) {
      this.push()
      return
    }
    const generation = this.beginQuickRun()
    const abortController = this.session.startAbortableOperation()
    try {
      if (!hasApiKey()) throw new MissingKeyError()
      const reviewDepth = depth ?? this.prefs.get().reviewDepth
      this.prefs.set({ mode, reviewDepth })
      this.setState('analysing')
      const answer = await runQuickAnalysis(
        source, text, focusQuestion.trim(), abortController.signal
      )
      if (!this.session.isCurrent(generation)) return
      this.finishQuick(answer, {
        runId: randomUUID(),
        source,
        artefact: text,
        focusQuestion: focusQuestion.trim()
      })
    } catch (err) {
      if (this.session.isCurrent(generation)) this.failQuick(err)
    } finally {
      this.session.finishAbortableOperation(abortController)
      this.gate.release()
      this.push()
    }
  }

  beginVoiceRecording(): string | undefined {
    if (!canTrigger(this.paused, this.gate.isBusy) || !this.gate.tryAcquire()) {
      this.push()
      return
    }
    this.session.invalidate()
    this.finding = null
    this.quickResult = null
    this.report = null
    this.error = null
    this.reviewPhase = 'quick'
    this.voiceSessionId = randomUUID()
    this.setState('recording')
    return this.voiceSessionId
  }

  cancelVoiceRecording(sessionId: string): void {
    if (this.voiceSessionId !== sessionId) return
    this.releaseVoiceRecordingReservation()
    this.session.invalidate()
    this.reviewPhase = null
    this.state = 'idle'
    this.push()
  }

  async runVoice(
    sessionId: string,
    bytes: Uint8Array,
    mimeType: VoiceMimeType,
    mode: AnalysisMode,
    focusQuestion = '',
    depth?: ReviewDepth
  ): Promise<boolean> {
    if (this.voiceSessionId !== sessionId || !this.gate.isBusy || this.paused) {
      this.push()
      bytes.fill(0)
      return false
    }
    this.voiceSessionId = null
    const generation = this.beginQuickRun()
    const abortController = this.session.startAbortableOperation()
    let transcript: string | null = null
    try {
      if (!hasApiKey()) throw new MissingKeyError()
      this.setState('transcribing')
      try {
        transcript = await requestTranscription(bytes, mimeType, abortController.signal)
      } finally {
        // The expert expansion reuses only the transcript, never raw audio.
        bytes.fill(0)
      }
      if (!this.session.isCurrent(generation)) return true
      const reviewDepth = depth ?? this.prefs.get().reviewDepth
      this.prefs.set({ mode, reviewDepth })
      this.setState('analysing')
      const answer = await runQuickAnalysis(
        'voice_transcript', transcript, focusQuestion.trim(), abortController.signal
      )
      if (!this.session.isCurrent(generation)) return true
      this.finishQuick(answer, {
        runId: randomUUID(),
        source: 'voice_transcript',
        artefact: transcript,
        focusQuestion: focusQuestion.trim()
      })
    } catch (err) {
      if (this.session.isCurrent(generation)) this.failQuick(err)
    } finally {
      transcript = null
      bytes.fill(0)
      this.session.finishAbortableOperation(abortController)
      this.gate.release()
      this.push()
    }
    return true
  }

  /** Consumes a quick run exactly once and launches the routed expert board. */
  async runFullReview(runId: string): Promise<boolean> {
    if (!canTrigger(this.paused, this.gate.isBusy) || !this.gate.tryAcquire()) return false
    const pending = this.session.takePending(runId)
    if (!pending) {
      this.gate.release()
      this.push()
      return false
    }
    const generation = this.session.nextGeneration()
    const abortController = this.session.startAbortableOperation()
    this.error = null
    this.finding = null
    this.report = null
    this.reviewPhase = 'full'
    this.wm.setMode('expanded')
    this.setState('analysing')
    try {
      const preferences = this.prefs.get()
      const report = await runExpertBoard(
        pending.source,
        pending.artefact,
        preferences.mode,
        preferences.reviewDepth,
        pending.focusQuestion,
        pending.runId,
        () => { pending.artefact = '' },
        abortController.signal
      )
      if (this.session.isCurrent(generation)) this.finishFull(report)
    } catch (err) {
      if (this.session.isCurrent(generation)) this.failFull(err)
    } finally {
      pending.artefact = ''
      this.session.finishAbortableOperation(abortController)
      this.gate.release()
      this.push()
    }
    return true
  }

  private beginQuickRun(): number {
    const generation = this.session.nextGeneration()
    this.session.clearPending()
    this.finding = null
    this.quickResult = null
    this.report = null
    this.error = null
    this.reviewPhase = 'quick'
    return generation
  }

  private finishQuick(answer: string, input: PendingReviewInput): void {
    const pending = this.session.retainPending(input)
    this.quickResult = { runId: pending.runId, answer }
    this.finding = null
    this.report = null
    this.error = null
    this.reviewPhase = 'quick'
    this.state = 'quick_result'
    this.wm.setMode('compact')
  }

  private finishFull(report: AnalysisReport): void {
    const finding = primaryFinding(report)
    this.quickResult = null
    this.report = report
    this.finding = finding
    this.error = null
    this.reviewPhase = 'full'
    this.state = finding.hasMaterialIssue ? 'result' : 'no_issue'
  }

  private failQuick(err: unknown): void {
    this.session.clearPending()
    this.error = toUserError(err, getModel())
    this.finding = null
    this.quickResult = null
    this.report = null
    this.reviewPhase = null
    this.state = 'error'
    console.warn(`[analysis] quick take failed: ${this.error.code}`)
    this.wm.setMode('compact')
  }

  private failFull(err: unknown): void {
    this.error = toUserError(err, getModel())
    this.finding = null
    this.report = null
    this.reviewPhase = 'full'
    this.state = 'error'
    console.warn(`[analysis] full review failed: ${this.error.code}`)
  }

  private releaseVoiceRecordingReservation(): void {
    if (!this.voiceSessionId) return
    this.voiceSessionId = null
    this.gate.release()
  }

  private setState(state: CompanionState): void {
    this.state = state
    this.push()
  }

  setWindowMode(mode: WindowMode): void {
    this.wm.setMode(mode)
    this.push()
  }

  fitHeight(contentHeight: number): void {
    this.wm.fitHeight(contentHeight)
  }

  togglePause(): void {
    this.paused = !this.paused
    if (this.paused) {
      this.session.invalidate()
      this.releaseVoiceRecordingReservation()
    }
    this.state = 'idle'
    this.push()
  }

  dismiss(): void {
    this.session.invalidate()
    this.releaseVoiceRecordingReservation()
    this.finding = null
    this.quickResult = null
    this.report = null
    this.error = null
    this.reviewPhase = null
    this.state = 'idle'
    this.wm.setMode('eye')
    this.push()
  }

  collapse(): void {
    this.wm.setMode(this.finding || this.quickResult || this.error ? 'compact' : 'eye')
    this.push()
  }

  quit(): void {
    this.session.invalidate()
    this.releaseVoiceRecordingReservation()
    app.quit()
  }
}
