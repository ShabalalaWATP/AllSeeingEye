import { app } from 'electron'
import { AnalysisGate } from './core/gate'
import { canTrigger, displayState } from './core/state'
import { toUserError } from './core/error-map'
import { MissingKeyError } from './core/errors'
import { captureDisplayUnderCursor } from './capture'
import { analyseImage, analyseText, getModel, hasApiKey } from './openai-client'
import type { WindowManager } from './window'
import type { PrefsStore } from './prefs'
import type {
  AnalysisMode,
  CompanionState,
  RedTeamFinding,
  StatePayload,
  UserError,
  WindowMode
} from '../shared/types'

/**
 * Owns the companion state machine. It lives in the main process because
 * triggers arrive from global shortcuts and the context menu even while the
 * renderer is busy. The renderer receives full snapshots and just renders.
 */
export class AnalysisController {
  private state: CompanionState = 'idle'
  private paused: boolean
  private finding: RedTeamFinding | null = null
  private error: UserError | null = null
  private readonly gate = new AnalysisGate()

  constructor(
    private wm: WindowManager,
    private prefs: PrefsStore
  ) {
    this.paused = prefs.get().startPaused
  }

  get isPaused(): boolean {
    return this.paused
  }

  snapshot(): StatePayload {
    const p = this.prefs.get()
    return {
      state: displayState(this.state, this.paused),
      windowMode: this.wm.mode,
      analysisMode: p.mode,
      paused: this.paused,
      privacyNoticeDismissed: p.privacyNoticeDismissed,
      finding: this.finding,
      error: this.error
    }
  }

  push(): void {
    if (this.wm.win.isDestroyed()) return
    this.wm.win.webContents.send('state', this.snapshot())
  }

  async runScreen(): Promise<void> {
    if (!canTrigger(this.paused, this.gate.isBusy) || !this.gate.tryAcquire()) {
      this.push()
      return
    }
    let dataUrl: string | null = null
    try {
      if (!hasApiKey()) throw new MissingKeyError()
      this.setState('capturing')
      dataUrl = await captureDisplayUnderCursor(this.wm.win)
      this.setState('analysing')
      const finding = await analyseImage(dataUrl, this.prefs.get().mode)
      this.finish(finding, false)
    } catch (err) {
      this.fail(err, false)
    } finally {
      dataUrl = null // drop the screenshot reference immediately
      this.gate.release()
      this.push()
    }
  }

  async runText(text: string, mode: AnalysisMode): Promise<void> {
    if (!canTrigger(this.paused, this.gate.isBusy) || !this.gate.tryAcquire()) {
      this.push()
      return
    }
    try {
      if (!hasApiKey()) throw new MissingKeyError()
      this.prefs.set({ mode })
      this.setState('analysing')
      const finding = await analyseText(text, mode)
      this.finish(finding, true)
    } catch (err) {
      this.fail(err, true)
    } finally {
      this.gate.release()
      this.push()
    }
  }

  private finish(finding: RedTeamFinding, keepWindow: boolean): void {
    this.finding = finding
    this.error = null
    this.state = finding.hasMaterialIssue ? 'result' : 'no_issue'
    if (!keepWindow && this.wm.mode === 'eye') this.wm.setMode('compact')
  }

  private fail(err: unknown, keepWindow: boolean): void {
    this.error = toUserError(err, getModel())
    this.finding = null
    this.state = 'error'
    console.warn(`[analysis] failed: ${this.error.code}`)
    if (!keepWindow && this.wm.mode === 'eye') this.wm.setMode('compact')
  }

  private setState(state: CompanionState): void {
    this.state = state
    this.push()
  }

  setWindowMode(mode: WindowMode): void {
    this.wm.setMode(mode)
    this.push()
  }

  togglePause(): void {
    this.paused = !this.paused
    if (!this.gate.isBusy) this.state = 'idle'
    this.push()
  }

  /** Dismiss the current finding or error and shrink back to the eye. */
  dismiss(): void {
    this.finding = null
    this.error = null
    if (!this.gate.isBusy) this.state = 'idle'
    this.wm.setMode('eye')
    this.push()
  }

  /** Escape from the expanded panel: back to compact if there is content. */
  collapse(): void {
    this.wm.setMode(this.finding || this.error ? 'compact' : 'eye')
    this.push()
  }

  quit(): void {
    app.quit()
  }
}
