import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../libs/api'

// UI components
import FixedBottomBar from '../components/FixedBottomBar'
import GradientButton from '../components/GradientButton'
import NeutralButton from '../components/NeutralButton'
import NewContactHeader from '../components/new-contact/NewContactHeader'
import NotesStep from '../components/new-contact/NotesStep'
import PhotoStep from '../components/new-contact/PhotoStep'
import ReviewStep, { type ContactDraft } from '../components/new-contact/ReviewStep'
import VoiceStep from '../components/new-contact/VoiceStep'

// Empty contact draft for initial and fallback states
function emptyDraft(): ContactDraft {
  return {
    display_name: null,
    email: null,
    phone: null,
    company: null,
    role: null,
    location: null,
    profile_text: null,
    keywords: null,
  }
}

export default function NewContactPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Step state (1 = image, 2 = voice, 3 = notes, 4 = review)
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1)

  // Image step state
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [ocrText, setOcrText] = useState('')

  // Transcription step state
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [transcript, setTranscript] = useState('')

  // Free-form text step state
  const [freeFormText, setFreeFormText] = useState('')

  // Review draft step state
  const [draft, setDraft] = useState<ContactDraft>(emptyDraft)

  // Build step state (LLM calling)
  const [isBuilding, setIsBuilding] = useState(false)

  // Individual step errors (only show the error if the user is still on that step)
  const [imageStepError, setImageStepError] = useState('')
  const [voiceStepError, setVoiceStepError] = useState('')
  const [notesStepError, setNotesStepError] = useState('')
  const [reviewStepError, setReviewStepError] = useState('')

  // Track the latest run ID for OCR and ASR so we can ignore previous (outdated) results
  const ocrRunIdRef = useRef(0)
  const asrRunIdRef = useRef(0)
  const ocrPromiseRef = useRef<Promise<void> | null>(null)
  const asrPromiseRef = useRef<Promise<void> | null>(null)

  // Create a preview URL when the user picks an image
  useEffect(() => {
    if (!imageFile) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(imageFile)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [imageFile])

  // Run OCR in the background when an image is selected
  useEffect(() => {
    // Clear the OCR text and error message
    setOcrText('')
    setImageStepError('')
    
    // If no image is selected, clear the promise ref
    if (!imageFile) {
      ocrPromiseRef.current = null
      return
    }

    // Increment the run ID for this OCR request
    const runId = ++ocrRunIdRef.current

    // Create a promise to run the OCR in the background
    const promise = (async () => {
      try {
        // Call the OCR API to extract text from the image
        const text = (await ocrImage(imageFile)).trim()
        
        // If the run ID is still the same, update the OCR text
        if (ocrRunIdRef.current === runId) setOcrText(text)
      } catch {
        // If the run ID is still the same, set the error message
        if (ocrRunIdRef.current === runId) {
          setImageStepError('Could not read the image. Try another image or skip this step.')
          setOcrText('')
        }
      }
    })()

    // Set the promise to the ref to track the latest run ID
    ocrPromiseRef.current = promise
  }, [imageFile])

  // Run transcription in the background when a recording is completed
  useEffect(() => {
    // Clear the transcript and error message
    setTranscript('')
    setVoiceStepError('')

    // If no audio is selected, clear the promise ref
    if (!audioBlob) {
      asrPromiseRef.current = null
      return
    }

    // Increment the run ID for this transcription request
    const runId = ++asrRunIdRef.current

    // Create a promise to run the transcription in the background
    const promise = (async () => {
      try {
        // Call the transcription API to transcribe the audio
        const nextTranscript = (await transcribeAudio(audioBlob)).trim()
        // If the run ID is still the same, update the transcript
        if (asrRunIdRef.current === runId) setTranscript(nextTranscript)

      } catch {
        // If the run ID is still the same, set the error message
        if (asrRunIdRef.current === runId) {
          setVoiceStepError('Could not transcribe the recording. You can add notes manually or skip.')
          setTranscript('')
        }
      }
    })()

    asrPromiseRef.current = promise
  }, [audioBlob])

  // Save the contact and return to the contacts list
  // Reference: https://tanstack.com/query/latest/docs/framework/react/reference/useMutation
  const saveMutation = useMutation({
    mutationFn: async (payload: ContactDraft) => {
      const response = await api.post('/contacts/', payload)
      return response.data
    },
    onSuccess: async () => {
      // Refetch contacts to update the contact list
      // Reference: https://tanstack.com/query/latest/docs/reference/QueryClient#queryclientinvalidatequeries
      await queryClient.invalidateQueries({ queryKey: ['contacts'] })
      navigate('/contacts')
    },
  })

  // Update a one of the field in the review draft
  function updateDraft(field: keyof ContactDraft, value: string | string[] | null) {
    setDraft(prev => ({ ...prev, [field]: value }))
  }

  // Close the create new contact flow by navigating to the contacts page
  function handleClose() {
    navigate('/contacts')
  }

  // Skip the current step
  function handleSkip() {
    if (step === 1) {
      // Skip the image step and move to the voice step
      setStep(2)
    } else if (step === 2) {
      // Skip voice step and move to the notes step
      setStep(3)
    } else if (step === 3) {
      // Skip notes step and move to the review step
      handleNotesContinue()
    }
  }

  // Extract text from a business card / profile image
  async function ocrImage(file: File): Promise<string> {
    // Create a new FormData object to send the image file to the backend
    const formData = new FormData()
    formData.append('file', file, file.name)
    
    // Send the image file to the OCR API
    const response = await api.post('/captures/ocr', formData)
    
    // Return the extracted text from the response
    return (response.data.text as string) ?? ''
  }

  // Transcribe a voice recording to text
  async function transcribeAudio(blob: Blob): Promise<string> {
    // Create a new FormData object to send the audio file to the backend
    const formData = new FormData()
    const filename = blob.type === 'audio/mp4' ? 'recording.mp4' : 'recording.webm'
    formData.append('file', blob, filename)
    
    // Send the audio file to the ASR API
    const response = await api.post('/captures/transcribe', formData)

    // Return the transcript from the response
    return (response.data.transcript as string) ?? ''
  }

  // Ask the LLM to structure OCR, transcript, and notes into contact fields
  async function buildDraft(
    transcriptText: string,
    ocrTextValue: string,
    freeFormTextValue: string,
  ): Promise<ContactDraft> {
    // Avoid a round-trip when the user skipped every capture step
    if (!transcriptText.trim() && !ocrTextValue.trim() && !freeFormTextValue.trim()) {
      return emptyDraft()
    }

    // Send the extracted text from OCR, transcript, and notes to the LLM API
    const response = await api.post('/captures/build-contact', {
      transcript: transcriptText,
      ocr_text: ocrTextValue,
      free_form_text: freeFormTextValue,
    })
    return response.data as ContactDraft
  }

  // Continue to the voice step
  function handlePhotoContinue() {
    setStep(2)
  }

  // Continue to the notes step
  function handleVoiceContinue() {
    setStep(3)
  }

  // Continue to the review step
  async function handleNotesContinue() {
    // Clear the notes and review step errors
    setNotesStepError('')
    setReviewStepError('')

    // If OCR/ASR are still running, wait here so the LLM uses the latest text
    await Promise.allSettled([ocrPromiseRef.current, asrPromiseRef.current].filter(Boolean))

    setIsBuilding(true)
    
    try {
      // Call the LLM API to build the contact draft
      const built = await buildDraft(transcript, ocrText, freeFormText)
      // Update the draft state with the response
      setDraft(built)
      // Move to the review step
      setStep(4)
    } catch {
      // Still land on review so the user can fill fields manually
      setReviewStepError('Could not build the profile. Please try again or edit the fields manually.')
      setDraft(emptyDraft())
      // Move to the review step
      setStep(4)
    } finally {
      setIsBuilding(false)
    }
  }

  // Save the contact
  async function handleSave() {
    setReviewStepError('')
    
    const name = (draft.display_name ?? '').trim()

    // If no name is provided, set the error message and return
    if (!name) {
      setReviewStepError('Add a name before saving.')
      return
    }

    try {
      // Save the contact draft
      // Reference: https://tanstack.com/query/latest/docs/framework/react/reference/useMutation
      await saveMutation.mutateAsync({
        ...draft,
        display_name: name,
        keywords: (draft.keywords ?? []).filter(Boolean),
      })
    } catch {
      // Set the error message
      setReviewStepError('Could not save this contact. Please try again.')
    }
  }

  // Only pass errors to the active step
  const imageError = step === 1 ? imageStepError : ''
  const voiceError = step === 2 ? voiceStepError : ''
  const notesError = step === 3 ? notesStepError : ''
  const reviewError = step === 4 ? reviewStepError : ''

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {/* Common header for all steps */}
      <NewContactHeader 
        step={step} 
        onClose={handleClose} 
      />

      {/* Step content */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-4 pt-5">
        {/* Image step */}
        {step === 1 ? (
          <PhotoStep
            previewUrl={previewUrl}
            onImageSelect={setImageFile}
            error={imageError}
          />
        ) : null}

        {/* Voice step */}
        {step === 2 ? (
          <VoiceStep 
            onRecordingComplete={setAudioBlob} 
            error={voiceError} 
          />
        ) : null}

        {/* Notes step */}
        {step === 3 ? (
          <NotesStep
            value={freeFormText}
            onChange={setFreeFormText}
            error={notesError}
          />
        ) : null}

        {/* Review step */}
        {step === 4 ? (
          <ReviewStep 
            draft={draft} 
            onChange={updateDraft} 
            error={reviewError} 
          />
        ) : null}
      </div>

      {/* Common bottom actions */}
      <FixedBottomBar>
        {/* Image step bottom actions */}
        {step === 1 ? (
          <div className="flex flex-col gap-3">
            <NeutralButton label="Skip" onClick={handleSkip} />
            <GradientButton onClick={handlePhotoContinue}>
              Continue
            </GradientButton>
          </div>
        ) : null}

        {/* Voice step bottom actions */}
        {step === 2 ? (
          <div className="flex flex-col gap-3">
            <NeutralButton label="Skip" onClick={handleSkip} />
            <GradientButton onClick={handleVoiceContinue}>
              Continue
            </GradientButton>
          </div>
        ) : null}

        {/* Notes step bottom actions */}
        {step === 3 ? (
          <div className="flex flex-col gap-3">
            <NeutralButton label="Skip" onClick={handleSkip} />
            {/* Only let the user continue if the LLM is done building the profile */}
            <GradientButton onClick={handleNotesContinue} disabled={isBuilding}>
              {isBuilding ? 'Building profile…' : 'Continue'}
            </GradientButton>
          </div>
        ) : null}

        {/* Review step bottom actions */}
        {step === 4 ? (
          // Only let the user save the contact if the backend is done saving
          <GradientButton onClick={handleSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? 'Saving…' : 'Save contact'}
          </GradientButton>
        ) : null}
      </FixedBottomBar>
    </div>
  )
}