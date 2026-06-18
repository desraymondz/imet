type StepTipProps = {
  children: string
}

export default function StepTip({ children }: StepTipProps) {
  return (
    <div className="flex items-start gap-3 rounded-[var(--r-lg)] bg-[var(--violet-light)]/60 px-4 py-3.5">
      {/* Sparkle icon */}
      <img src="/ui/sparkle.svg" alt="" className="mt-1 size-4 shrink-0" aria-hidden />

      {/* Step tip text */}
      <p className="leading-relaxed text-[var(--fg-2)]">{children}</p>
    </div>
  )
}