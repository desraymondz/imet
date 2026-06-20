import { useEffect, useState } from 'react'
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

  // Shared UI state (loading, error)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

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
    // Clear the error message
    setError('')
    if (step === 1) {
      // Skip the image step and move to the voice step
      setStep(2)
    } else if (step === 2) {
      // Skip voice step and move to the notes step
      handleVoiceContinue(true)
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
    const response = await api.post('/captures/ocr', formData, {
      // Set the content type to multipart/form-data
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    
    // Return the extracted text from the response
    return (response.data.text as string) ?? ''
  }

  // Transcribe a voice recording to text
  async function transcribeAudio(blob: Blob): Promise<string> {
    // Create a new FormData object to send the audio file to the backend
    const formData = new FormData()
    formData.append('file', blob, 'recording.webm')
    
    // Send the audio file to the ASR API
    const response = await api.post('/captures/transcribe', formData, {
      // Set the content type to multipart/form-data
      headers: { 'Content-Type': 'multipart/form-data' },
    })

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
  async function handlePhotoContinue() {
    // Clear the error message
    setError('')
    // If no image is selected, move to the voice step
    if (!imageFile) {
      setStep(2)
      return
    }

    // Set the loading state to true
    setIsLoading(true)
    try {
      // Extract text from the image
      const text = (await ocrImage(imageFile)).trim()
      // Update the OCR text state
      setOcrText(text)
      // Move to the voice step
      setStep(2)
    } catch {
      // Set the error message
      setError('Could not read the image. Try another photo or skip this step.')
    } finally {
      // Set the loading state to false
      setIsLoading(false)
    }
  }

  // Continue to the notes step
  async function handleVoiceContinue(skipTranscribe = false) {
    // Clear the error message
    setError('')
    // Move to the notes step when user skips it
    if (skipTranscribe) {
      setStep(3)
      return
    }

    // Set the loading state to true
    setIsLoading(true)
    try {
      let finalTranscript = ''
      // Call the ASR API to transcribe the audio
      if (audioBlob) {
        finalTranscript = (await transcribeAudio(audioBlob)).trim()
      }
      
      // Update the transcript state
      setTranscript(finalTranscript)
      // Move to the notes step
      setStep(3)
    } catch {
      setError('Could not transcribe the recording. You can add notes manually or skip.')
    } finally {
      setIsLoading(false)
    }
  }

  // Continue to the review step
  async function handleNotesContinue() {
    // Clear the error message
    setError('')
    // Set the loading state to true
    setIsLoading(true)
    
    try {
      // Call the LLM API to build the contact draft
      const built = await buildDraft(transcript, ocrText, freeFormText)
      // Update the draft state with the response
      setDraft(built)
      // Move to the review step
      setStep(4)
    } catch {
      // Still land on review so the user can fill fields manually
      setError('Could not build the profile. Please try again or edit the fields manually.')
      setDraft(emptyDraft())
      // Move to the review step
      setStep(4)
    } finally {
      setIsLoading(false)
    }
  }

  // Save the contact
  async function handleSave() {
    setError('')
    
    const name = (draft.display_name ?? '').trim()

    // If no name is provided, set the error message and return
    if (!name) {
      setError('Add a name before saving.')
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
      setError('Could not save this contact. Please try again.')
    }
  }

  // Only pass errors to the active step
  const photoError = step === 1 ? error : ''
  const voiceError = step === 2 ? error : ''
  const notesError = step === 3 ? error : ''
  const reviewError = step === 4 ? error : ''

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {/* Common header for all steps */}
      <NewContactHeader 
        step={step} 
        onClose={handleClose} 
      />

      {/* Step content */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-4 pt-5">
        {/* Photo step */}
        {step === 1 ? (
          <PhotoStep
            previewUrl={previewUrl}
            onImageSelect={setImageFile}
            error={photoError}
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
        {/* Photo step bottom actions */}
        {step === 1 ? (
          <div className="flex flex-col gap-3">
            <NeutralButton label="Skip" onClick={handleSkip} />
            <GradientButton onClick={handlePhotoContinue} disabled={isLoading}>
              {isLoading ? 'Reading card…' : 'Continue'}
            </GradientButton>
          </div>
        ) : null}

        {/* Voice step bottom actions */}
        {step === 2 ? (
          <div className="flex flex-col gap-3">
            <NeutralButton label="Skip" onClick={handleSkip} />
            <GradientButton onClick={() => handleVoiceContinue()} disabled={isLoading}>
              {isLoading ? 'Transcribing…' : 'Continue'}
            </GradientButton>
          </div>
        ) : null}

        {/* Notes step bottom actions */}
        {step === 3 ? (
          <div className="flex flex-col gap-3">
            <NeutralButton label="Skip" onClick={handleSkip} />
            <GradientButton onClick={handleNotesContinue} disabled={isLoading}>
              {isLoading ? 'Building profile…' : 'Continue'}
            </GradientButton>
          </div>
        ) : null}

        {/* Review step bottom actions */}
        {step === 4 ? (
          <GradientButton onClick={handleSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? 'Saving…' : 'Save contact'}
          </GradientButton>
        ) : null}
      </FixedBottomBar>
    </div>
  )
}