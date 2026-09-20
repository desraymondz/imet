import { Loader2 } from 'lucide-react'

type SpinnerProps = {
  label?: string
}

export default function Spinner({ label = 'Loading' }: SpinnerProps) {
  return (
    // Centered loading spinner
    <div
      className="flex flex-1 items-center justify-center py-10"
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <Loader2
        className="size-8 animate-spin text-[var(--violet)]"
        aria-hidden
      />
      <span className="sr-only">{label}</span>
    </div>
  )
}