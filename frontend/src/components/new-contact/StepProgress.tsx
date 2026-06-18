// Step progress indicator for the new contact page

type StepProgressProps = {
  step: 1 | 2 | 3 | 4
}

export default function StepProgress({ step }: StepProgressProps) {
  return (
    <div className="flex gap-1.5 px-1">
      {[1, 2, 3, 4].map(n => (
        // Step indicator with a gradient background if the step is completed
        <div
          key={n}
          className="h-1 flex-1 overflow-hidden rounded-full bg-[var(--hairline-2)]"
        >
          {n <= step ? (
            <div className="h-full w-full rounded-full bg-[linear-gradient(96deg,var(--violet),var(--blue))]" />
          ) : null}
        </div>
      ))}
    </div>
  )
}
