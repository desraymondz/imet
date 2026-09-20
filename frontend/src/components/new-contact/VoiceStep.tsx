import { useCallback, useEffect, useRef, useState } from 'react'
import StepTip from './StepTip'

type VoiceStepProps = {
  transcript: string
  onTranscriptChange: (value: string) => void
  onRecordingComplete: (blob: Blob) => void
  onRecordingReset: () => void
  onRecordingChange: (isRecording: boolean) => void
  isTranscribing: boolean
  hasSavedTake?: boolean
  error?: string
}

// Format the time in minutes and seconds into MM:SS
function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function VoiceStep({
  transcript,
  onTranscriptChange,
  onRecordingComplete,
  onRecordingReset,
  onRecordingChange,
  isTranscribing,
  hasSavedTake = false,
  error,
}: VoiceStepProps) {
  // State for recording
  const [isRecording, setIsRecording] = useState(false)
  const [hasRecording, setHasRecording] = useState(hasSavedTake)
  const [elapsed, setElapsed] = useState(0)

  // State for microphone error
  const [micError, setMicError] = useState('')

  // Reference to the media recorder
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)

  // Reference to the chunks
  const chunksRef = useRef<Blob[]>([])

  // Reference to the timer
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Ignore onstop from a take that was discarded on unmount / skip
  const isMountedRef = useRef(true)

  // Stop recording handler
  const stopRecording = useCallback(() => {
    // Clear the timer
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    // Stop the recording if it is recording
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    // Update local recording state.
    setIsRecording(false)
  }, [])

  // Start recording handler
  const startRecording = useCallback(async () => {
    // Reset microphone error
    setMicError('')

    // Try to get user media
    try {
      // Get the user media stream using the microphone
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // Discard the previous take now that the mic is actually available
      onRecordingReset()
      setHasRecording(false)

      // Check if the media recorder supports the mime type
      // Reference: https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4'

      // Create a new media recorder using the media stream and the mime type
      const recorder = new MediaRecorder(stream, { mimeType })
      // Reset the chunks to an empty array
      chunksRef.current = []

      // Once data chunk is available, add to the chunks
      recorder.ondataavailable = e => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      // Once the recording is stopped, get the blob and call the onRecordingComplete callback
      recorder.onstop = () => {
        // Stop the stream
        stream.getTracks().forEach(t => t.stop())

        // Merge the chunks into a single blob
        const blob = new Blob(chunksRef.current, { type: mimeType })
        // Update states if the blob successfully merged
        if (blob.size > 0 && isMountedRef.current) {
          onRecordingComplete(blob)
          setHasRecording(true)
        }
        onRecordingChange(false)
      }

      // Update the media recorder reference
      mediaRecorderRef.current = recorder

      // Start the recording
      recorder.start()
      setIsRecording(true)
      onRecordingChange(true)
      setElapsed(0)
      // Set the timer to increment the elapsed time every second
      timerRef.current = setInterval(() => setElapsed(s => s + 1), 1000)
    } catch {
      setMicError('Microphone access denied.')
    }
  }, [onRecordingChange, onRecordingComplete, onRecordingReset])

  // Cleanup function
  useEffect(() => {
    isMountedRef.current = true
    // Stop the recording when the component unmounts
    return () => {
      isMountedRef.current = false
      stopRecording()
    }
  }, [stopRecording])

  // Recording status line
  const statusText = isRecording
    ? 'Recording…'
    : hasRecording
      ? 'Recording saved'
      : 'Tap to start recording'

  return (
    <div className="flex flex-col gap-5">
      <h1>Say what you remember</h1>

      {/* Microphone error */}
      {micError ? (
        <p className="text-error">{micError}</p>
      ) : null}

      {/* Transcription error */}
      {error ? (
        <p className="text-error">{error}</p>
      ) : null}

      <div className="flex flex-col items-center gap-4 py-4">
        {/* Elapsed time */}
        <p className="font-bold tabular-nums leading-none text-[var(--fg)]">
          {formatTime(elapsed)}
        </p>

        {/* Recording status */}
        <p className="text-[var(--fg-3)]">
          {statusText}
        </p>

        {/* Record / stop button (hidden after a take) */}
        {isRecording || !hasRecording ? (
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={!!micError}
            className="flex size-20 items-center justify-center rounded-full bg-[var(--violet-light)] shadow-[var(--shadow)]"
            aria-label={isRecording ? 'Stop recording' : 'Start recording'}
          >
            {/* Stop button */}
            {isRecording ? (
              <span className="font-semibold text-[var(--violet-deep)]">Stop</span>
            ) : (
              <img src="/ui/mic.svg" alt="" className="size-8" aria-hidden />
            )}
          </button>
        ) : null}
      </div>
      {/* Voice step tip (hide once the transcript is on screen) */}
      {!hasRecording || isRecording || isTranscribing ? (
        <StepTip>Where you met, what they're into, and anything else you remember. We'll structure it.</StepTip>
      ) : null}

      {/* Transcript (shown after a take is saved) */}
      {hasRecording && !isRecording ? (
        <div className="flex flex-col gap-4">
          {isTranscribing ? (
            <p className="text-center text-[var(--fg-3)]">Transcribing…</p>
          ) : (
            <label className="field">
              <span className="field-label">Transcript</span>
              <textarea
                className="input min-h-72 resize-none leading-relaxed"
                placeholder="No speech detected."
                value={transcript}
                onChange={e => onTranscriptChange(e.target.value)}
              />
            </label>
          )}

          {/* Record again */}
          <button
            type="button"
            onClick={startRecording}
            className="self-center text-sm font-semibold text-[var(--violet-deep)]"
          >
            Record again
          </button>
        </div>
      ) : null}
    </div>
  )
}