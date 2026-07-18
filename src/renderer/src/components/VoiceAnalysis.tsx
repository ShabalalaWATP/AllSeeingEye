import { useEffect, useRef, useState } from 'react'
import { isBusy } from '../hooks'
import {
  ALLOWED_VOICE_MIME_TYPES,
  MAX_VOICE_BYTES,
  MAX_VOICE_SECONDS,
  type AnalysisMode,
  type ReviewDepth,
  type StatePayload,
  type VoiceMimeType
} from '../../../shared/types'

type VoiceStage = 'requesting' | 'recording' | 'processing' | 'ready'

export default function VoiceAnalysis({
  snapshot,
  activationId
}: {
  snapshot: StatePayload
  activationId: number
}): React.JSX.Element {
  const [stage, setStage] = useState<VoiceStage>('requesting')
  const [elapsedMs, setElapsedMs] = useState(0)
  const [error, setError] = useState('')
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startedAtRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const generationRef = useRef(0)
  const startPendingRef = useRef(false)
  const doneRequestedRef = useRef(false)
  const lastActivationRef = useRef(0)
  const sessionIdRef = useRef<string | null>(null)
  const settingsRef = useRef<{ mode: AnalysisMode; depth: ReviewDepth }>({
    mode: snapshot.analysisMode,
    depth: snapshot.reviewDepth
  })
  settingsRef.current = { mode: snapshot.analysisMode, depth: snapshot.reviewDepth }

  const busy = isBusy(snapshot.state)

  const releaseMedia = (): void => {
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = null
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    recorderRef.current = null
  }

  const invalidateRecording = (): void => {
    generationRef.current += 1
    doneRequestedRef.current = false
    const recorder = recorderRef.current
    if (recorder) {
      recorder.ondataavailable = null
      recorder.onstop = null
      recorder.onerror = null
      if (recorder.state !== 'inactive') recorder.stop()
    }
    chunksRef.current = []
    releaseMedia()
  }

  const releaseSession = async (): Promise<void> => {
    const sessionId = sessionIdRef.current
    sessionIdRef.current = null
    if (sessionId) await window.criticalEye.cancelVoiceRecording(sessionId)
  }

  useEffect(() => () => {
    invalidateRecording()
    void releaseSession()
  }, [])

  const close = async (): Promise<void> => {
    invalidateRecording()
    await releaseSession()
    setElapsedMs(0)
    setError('')
    await window.criticalEye.dismiss()
  }

  const chooseMime = (): VoiceMimeType | null => {
    for (const candidate of ALLOWED_VOICE_MIME_TYPES) {
      if (MediaRecorder.isTypeSupported(candidate)) return candidate
    }
    return null
  }

  const submitRecording = async (
    chunks: Blob[],
    mimeType: VoiceMimeType,
    durationMs: number,
    generation: number
  ): Promise<void> => {
    let bytes: ArrayBuffer | null = null
    try {
      if (durationMs < 500) throw new Error('The voice note was too short. Record a little longer.')
      if (chunks.length === 0) throw new Error('No audio was captured. Please try again.')
      bytes = await new Blob(chunks, { type: mimeType }).arrayBuffer()
      if (generationRef.current !== generation) return
      if (bytes.byteLength === 0) throw new Error('No audio was captured. Please try again.')
      if (bytes.byteLength > MAX_VOICE_BYTES) {
        throw new Error('The recording exceeded the 10 MB safety limit and was discarded.')
      }
      const sessionId = sessionIdRef.current
      if (!sessionId) throw new Error('The voice recording session expired. Please try again.')
      const { mode, depth } = settingsRef.current
      const request = window.criticalEye.analyseVoice(
        sessionId,
        bytes,
        mimeType,
        durationMs,
        mode,
        '',
        depth
      )
      sessionIdRef.current = null
      new Uint8Array(bytes).fill(0)
      bytes = null
      const accepted = await request
      if (generationRef.current !== generation) return
      if (!accepted) throw new Error('AllSeeingEye is already busy. Please try again.')
    } catch (caught) {
      if (generationRef.current !== generation) return
      await releaseSession()
      setError(caught instanceof Error ? caught.message : 'The voice note could not be analysed.')
      setStage('ready')
      setElapsedMs(0)
    } finally {
      if (bytes) new Uint8Array(bytes).fill(0)
    }
  }

  const done = (): void => {
    const recorder = recorderRef.current
    if (!recorder || recorder.state !== 'recording' || doneRequestedRef.current) return
    if (performance.now() - startedAtRef.current < 500) return
    doneRequestedRef.current = true
    setStage('processing')
    recorder.stop()
  }

  const start = async (): Promise<void> => {
    if (startPendingRef.current || recorderRef.current || busy || snapshot.paused) return
    startPendingRef.current = true
    setError('')
    setElapsedMs(0)
    setStage('requesting')
    const generation = generationRef.current + 1
    generationRef.current = generation
    doneRequestedRef.current = false
    try {
      const sessionId = await window.criticalEye.beginVoiceRecording()
      if (!sessionId) throw new Error('AllSeeingEye is already busy. Please try again.')
      if (generationRef.current !== generation) {
        await window.criticalEye.cancelVoiceRecording(sessionId)
        return
      }
      sessionIdRef.current = sessionId
      const selectedMime = chooseMime()
      if (!selectedMime) throw new Error('This system does not provide a supported voice format.')
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
        video: false
      })
      if (generationRef.current !== generation) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      streamRef.current = stream
      const recorder = new MediaRecorder(stream, {
        mimeType: selectedMime,
        audioBitsPerSecond: 64_000
      })
      recorderRef.current = recorder
      chunksRef.current = []
      startedAtRef.current = performance.now()
      setStage('recording')

      recorder.ondataavailable = (event) => {
        if (generationRef.current !== generation || event.data.size === 0) return
        chunksRef.current.push(event.data)
        const totalBytes = chunksRef.current.reduce((sum, chunk) => sum + chunk.size, 0)
        if (totalBytes > MAX_VOICE_BYTES) {
          setError('The recording exceeded the 10 MB safety limit and was discarded.')
          invalidateRecording()
          void releaseSession()
          setStage('ready')
        }
      }
      recorder.onerror = () => {
        if (generationRef.current !== generation) return
        setError('Recording stopped unexpectedly. Try again.')
        invalidateRecording()
        void releaseSession()
        setStage('ready')
      }
      recorder.onstop = () => {
        if (generationRef.current !== generation || !doneRequestedRef.current) return
        const durationMs = Math.min(
          MAX_VOICE_SECONDS * 1_000,
          Math.round(performance.now() - startedAtRef.current)
        )
        const chunks = chunksRef.current
        chunksRef.current = []
        releaseMedia()
        void submitRecording(chunks, selectedMime, durationMs, generation)
      }
      recorder.start(250)
      timerRef.current = setInterval(() => {
        const nextElapsed = Math.floor(performance.now() - startedAtRef.current)
        setElapsedMs(nextElapsed)
        if (nextElapsed >= MAX_VOICE_SECONDS * 1_000 && recorder.state === 'recording') done()
      }, 100)
    } catch (caught) {
      if (generationRef.current !== generation) return
      const name = caught instanceof DOMException ? caught.name : ''
      setError(name === 'NotAllowedError'
        ? 'Microphone access is blocked. Allow AllSeeingEye in Windows microphone privacy settings, then try again.'
        : name === 'NotFoundError'
          ? 'No microphone was found.'
          : name === 'NotReadableError'
            ? 'The microphone is being used by another app.'
            : caught instanceof Error ? caught.message : 'Could not start recording.')
      releaseMedia()
      await releaseSession()
      setStage('ready')
    } finally {
      startPendingRef.current = false
    }
  }

  // The zero-delay timer is cancelled by React Strict Mode's first effect pass,
  // preventing duplicate permission requests while preserving explicit activation.
  useEffect(() => {
    if (activationId <= 0 || lastActivationRef.current === activationId) return
    const timer = setTimeout(() => {
      if (lastActivationRef.current === activationId) return
      lastActivationRef.current = activationId
      void start()
    }, 0)
    return () => clearTimeout(timer)
  }, [activationId])

  useEffect(() => {
    if (!snapshot.paused || !sessionIdRef.current) return
    invalidateRecording()
    void releaseSession()
    setError('Recording was cancelled because AllSeeingEye was paused.')
    setStage('ready')
  }, [snapshot.paused])

  const seconds = Math.floor(elapsedMs / 1_000)
  const timerLabel = `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`
  const processingLabel = snapshot.state === 'transcribing'
    ? 'Transcribing…'
    : snapshot.state === 'analysing'
      ? 'Getting a quick take…'
      : 'Preparing your voice note…'

  return (
    <div className="voice-analysis minimal-input" onKeyDownCapture={(event) => {
      if (event.key === 'Escape' && (stage === 'requesting' || stage === 'recording')) {
        event.preventDefault()
        event.stopPropagation()
        close()
      }
    }}>
      <div className="voice-live" aria-live="polite">
        {stage === 'requesting' && <p>Waiting for microphone…</p>}
        {stage === 'recording' && (
          <p><span className="recording-dot" /> Listening… <strong>{timerLabel}</strong></p>
        )}
        {stage === 'processing' && <p>{processingLabel}</p>}
        {stage === 'ready' && !error && <p>Ready to try again.</p>}
      </div>

      <div className="voice-controls">
        {stage === 'requesting' && (
          <button className="btn subtle" onClick={() => void close()}>Cancel</button>
        )}
        {stage === 'recording' && (
          <>
            <button className="btn primary stop" autoFocus disabled={elapsedMs < 500} onClick={done}>
              Done
            </button>
            <button className="btn subtle" onClick={() => void close()}>Cancel</button>
          </>
        )}
        {stage === 'ready' && (
          <>
            <button className="btn primary" autoFocus disabled={busy || snapshot.paused} onClick={() => void start()}>
              Try again
            </button>
            <button className="btn subtle" onClick={() => void close()}>Close</button>
          </>
        )}
      </div>

      {error && <div className="error-banner" role="alert"><p>{error}</p></div>}
      {snapshot.error && <div className="error-banner" role="alert"><p>{snapshot.error.message}</p></div>}
      <p className="capture-scope voice-scope">
        Done sends the audio for transcription and a quick answer. App-owned audio buffers are then released; the transcript is held briefly so Full analysis remains available.
      </p>
    </div>
  )
}
