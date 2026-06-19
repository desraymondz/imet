import { useState } from 'react'
import InitialAvatar from '../InitialAvatar'

export type ContactDraft = {
  display_name: string | null
  email: string | null
  phone: string | null
  company: string | null
  role: string | null
  location: string | null
  profile_text: string | null
  keywords: string[] | null
}

type ReviewStepProps = {
  draft: ContactDraft
  onChange: (field: keyof ContactDraft, value: string | string[] | null) => void
  error?: string
}

// Parse comma-separated tags into a list of keywords
function parseKeywords(text: string): string[] | null {
  const items = text.split(',').map(k => k.trim()).filter(Boolean)
  return items.length > 0 ? items : null
}

export default function ReviewStep({ draft, onChange, error }: ReviewStepProps) {
  // The keywords text showed in the keywords input
  const [keywordsText, setKeywordsText] = useState(() => (draft.keywords ?? []).join(', '))

  return (
    <div className="flex flex-col gap-5">
      <h1>Review</h1>

      {/* Error message */}
      {error ? (
        <p className="text-error">{error}</p>
      ) : null}

      {/* Profile */}
      <div className="flex flex-col items-center gap-3 pt-2 text-center">
        {/* Avatar with name initials */}
        <InitialAvatar
          name={draft.display_name ?? ''}
          sizeClassName="size-24"
          className="text-4xl"
        />

        {/* Display name input */}
        <label className="field w-full max-w-70">
          <span className="sr-only">Display name</span>
          <input
            className="input text-center font-bold"
            value={draft.display_name ?? ''}
            onChange={e => onChange('display_name', e.target.value || null)}
            placeholder="Display name"
          />
        </label>

        {/* Keywords input */}
        <label className="field w-full max-w-80">
          <span className="sr-only">Keywords</span>
          <input
            className="input text-center"
            value={keywordsText}
            onChange={e => {
              // Update the keywords text
              const next = e.target.value
              setKeywordsText(next)
              onChange('keywords', parseKeywords(next))
            }}
            placeholder="Keywords (comma-separated)"
          />
        </label>
      </div>

      {/* Summary */}
      <div className="rounded-[var(--r-lg)] bg-[var(--violet-light)]/70 px-5 py-5">
        <div className="flex items-center gap-2">
          {/* Sparkle icon */}
          <img src="/ui/sparkle.svg" alt="" className="size-4" aria-hidden />

          {/* Summary label */}
          <span className="text-xs font-semibold tracking-[0.08em] text-[var(--violet-deep)]">
            SUMMARY
          </span>
        </div>

        {/* Summary text area */}
        <label className="field mt-3">
          <span className="sr-only">Summary</span>
          <textarea
            className="input min-h-50 resize-none border-0 leading-relaxed"
            value={draft.profile_text ?? ''}
            onChange={e => onChange('profile_text', e.target.value || null)}
            placeholder="No summary yet."
          />
        </label>
      </div>

      {/* Details */}
      <div>
        <p className="mb-3 text-xs font-semibold tracking-[0.08em] text-[var(--fg-3)]">
          DETAILS
        </p>
        <div className="divide-y divide-[var(--hairline)] overflow-hidden rounded-[var(--r-lg)] border border-[var(--hairline)] bg-white/80 shadow-[var(--shadow)]">
          {/* Email */}
          <div className="flex items-center justify-between gap-4 px-4 py-3.5">
            <span className="text-sm text-[var(--fg-3)]">Email</span>
            <input
              className="input max-w-50 py-2 text-right text-sm"
              value={draft.email ?? ''}
              onChange={e => onChange('email', e.target.value || null)}
              placeholder="—"
            />
          </div>

          {/* Phone */}
          <div className="flex items-center justify-between gap-4 px-4 py-3.5">
            <span className="text-sm text-[var(--fg-3)]">Phone</span>
            <input
              className="input max-w-50 py-2 text-right text-sm"
              value={draft.phone ?? ''}
              onChange={e => onChange('phone', e.target.value || null)}
              placeholder="—"
            />
          </div>

          {/* Company */}
          <div className="flex items-center justify-between gap-4 px-4 py-3.5">
            <span className="text-sm text-[var(--fg-3)]">Company</span>
            <input
              className="input max-w-50 py-2 text-right text-sm"
              value={draft.company ?? ''}
              onChange={e => onChange('company', e.target.value || null)}
              placeholder="—"
            />
          </div>
          
          {/* Role */}
          <div className="flex items-center justify-between gap-4 px-4 py-3.5">
            <span className="text-sm text-[var(--fg-3)]">Role</span>
            <input
              className="input max-w-50 py-2 text-right text-sm"
              value={draft.role ?? ''}
              onChange={e => onChange('role', e.target.value || null)}
              placeholder="—"
            />
          </div>

          {/* Location */}
          <div className="flex items-center justify-between gap-4 px-4 py-3.5">
            <span className="text-sm text-[var(--fg-3)]">Location</span>
            <input
              className="input max-w-50 py-2 text-right text-sm"
              value={draft.location ?? ''}
              onChange={e => onChange('location', e.target.value || null)}
              placeholder="—"
            />
          </div>
        </div>
      </div>
    </div>
  )
}