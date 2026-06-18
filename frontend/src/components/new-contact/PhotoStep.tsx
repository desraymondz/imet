import { useRef, type ChangeEvent } from 'react'
import StepTip from './StepTip'

type PhotoStepProps = {
  previewUrl: string | null
  onImageSelect: (file: File) => void
  error?: string
}

export default function PhotoStep({ previewUrl, onImageSelect, error }: PhotoStepProps) {
  // Reference to the hidden file input
  const fileRef = useRef<HTMLInputElement>(null)

  // Hidden file input change handler to reset the input after the file is chosen
  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) onImageSelect(file)
    e.target.value = ''
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="font-bold">Add a Business Card or LinkedIn Profile</h1>
      </div>

      {/* Upload button */}
      <button
        type="button"
        onClick={() => fileRef.current?.click()}
        className="flex w-full flex-col items-center justify-center gap-3 rounded-[var(--r-lg)] border-2 border-dashed border-[var(--violet)] bg-white/50 px-6 py-10 text-left"
        aria-label={previewUrl ? 'Change image' : 'Upload an image of the business card or LinkedIn profile'}
      >
        {/* Preview image */}
        {previewUrl ? (
          <img
            src={previewUrl}
            alt="Upload an image of the business card or LinkedIn profile"
            className="max-h-[200px] w-full rounded-[14px] object-contain"
          />
        ) : (
          <>
            {/* Upload icon */}
            <div className="flex size-14 items-center justify-center rounded-[16px] bg-[var(--violet-light)]">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="currentColor"
                className="size-7 text-[var(--violet-deep)]"
                viewBox="0 0 16 16"
                aria-hidden
              >
                <path d="M.002 3a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-12a2 2 0 0 1-2-2zm1 9v1a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9.5l-3.777-1.947a.5.5 0 0 0-.577.093l-3.71 3.71-2.66-1.772a.5.5 0 0 0-.63.062zm5-6.5a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0" />
              </svg>
            </div>

            {/* Upload text */}
            <p className="text-center leading-relaxed text-[var(--fg-3)]">
              Tap to choose from your photo library.
            </p>
          </>
        )}
      </button>

      {/* Hidden input to upload the image */}
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Photo step tip */}
      <StepTip>Text on the image is extracted automatically</StepTip>

      {/* Error message */}
      {error ? <p className="text-error">{error}</p> : null}
    </div>
  )
}