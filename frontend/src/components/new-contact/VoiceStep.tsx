import { useCallback, useEffect, useRef, useState } from 'react'
import StepTip from './StepTip'

type VoiceStepProps = {
  onRecordingComplete: (blob: Blob) => void
}

// Format the time in minutes and seconds into MM:SS
function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function VoiceStep({ onRecordingComplete }: VoiceStepProps) {
  // State for recording
  const [isRecording, setIsRecording] = useState(false)
  const [hasRecording, setHasRecording] = useState(false)
  const [elapsed, setElapsed] = useState(0)

  // State for microphone error
  const [micError, setMicError] = useState('')

  // Reference to the media recorder
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)

  // Reference to the chunks
  const chunksRef = useRef<Blob[]>([])

  // Reference to the timer
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
    // Update state
    setIsRecording(false)
  }, [])

  // Start recording handler
  const startRecording = useCallback(async () => {
    // Reset microphone error and recording state
    setMicError('')
    setHasRecording(false)

    // Try to get user media
    try {
      // Get the user media stream using the microphone
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
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
        if (blob.size > 0) {
          onRecordingComplete(blob)
          setHasRecording(true)
        }
      }

      // Update the media recorder reference
      mediaRecorderRef.current = recorder
      
      // Start the recording
      recorder.start()
      setIsRecording(true)
      setElapsed(0)
      // Set the timer to increment the elapsed time every second
      timerRef.current = setInterval(() => setElapsed(s => s + 1), 1000)
    } catch {
      setMicError('Microphone access denied.')
    }
  }, [onRecordingComplete])

  // Cleanup function
  useEffect(() => {
    // Stop the recording when the component unmounts
    return () => {
      stopRecording()
    }
  }, [stopRecording])

  return (
    <div className="flex flex-col gap-5">
      <h1>Say what you remember</h1>

      {/* Error message */}
      {micError ? (
        <p className="text-[14px] text-[var(--danger)]">{micError}</p>
      ) : null}

      <div className="flex flex-col items-center gap-4 py-4">
        {/* Elapsed time */}
        <p className="font-bold tabular-nums leading-none text-[var(--fg)]">
          {formatTime(elapsed)}
        </p>

        {/* Recording status */}
        <p className="text-[var(--fg-3)]">
          {isRecording ? 'Recording…' : hasRecording ? 'Recording saved' : 'Tap to start recording'}
        </p>

        {/* Record button */}
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
      </div>

      {/* Voice step tip */}
      <StepTip>Where you met, what they're into, and anything else you remember. We'll structure it.</StepTip>
    </div>
  )
}