type NotesStepProps = {
  value: string
  onChange: (value: string) => void
  error?: string
}

export default function NotesStep({ value, onChange, error }: NotesStepProps) {
  return (
    <div className="flex flex-col gap-5">
      <h1>Anything else?</h1>

      {/* Error message */}
      {error ? (
        <p className="text-error">{error}</p>
      ) : null}

      {/* Notes input */}
      <label className="field">
        <span className="sr-only">Notes</span>
        <textarea
          className="input min-h-100 resize-none leading-relaxed"
          placeholder="e.g. Met at ABC Coffee Shop, Looking for a co-founder in ..."
          value={value}
          onChange={e => onChange(e.target.value)}
        />
      </label>
    </div>
  )
}