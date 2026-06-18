import StepProgress from './StepProgress'

type NewContactHeaderProps = {
  step: 1 | 2 | 3 | 4
  onClose: () => void
}

export default function NewContactHeader({ step, onClose }: NewContactHeaderProps) {
  return (
    <header className="px-5 pt-5">
      <button
        type="button"
        onClick={onClose}
        className="flex size-10 items-center justify-center rounded-full text-[var(--fg-2)]"
        aria-label="Close"
      >
          {/* Close icon */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="currentColor"
            className="size-6"
            viewBox="0 0 16 16"
            aria-hidden
          >
            <path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8z" />
          </svg>
      </button>

      <div className="mt-4">
        <StepProgress step={step} />
      </div>
    </header>
  )
}