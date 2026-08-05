import { Link } from 'react-router-dom'
import InitialAvatar from './InitialAvatar'
import KeywordPill from './KeywordPill'
import type { Contact } from '../types/contact'

type ContactCardProps = {
  contact: Contact
  score?: number
}

export default function ContactCard({ contact, score }: ContactCardProps) {
  // Get the contact name
  const name = (contact.display_name ?? '').trim() || '—'
  // Get the contact profile text
  const profileText = (contact.profile_text ?? '').trim() || 'No profile text yet.'
  // Get the contact keywords
  const keywords = (contact.keywords ?? []).filter(Boolean).slice(0, 6)

  return (
    <Link
      to={`/contacts/${contact.id}/edit`}
      className="block rounded-[var(--r-lg)] border border-[var(--hairline)] bg-[var(--bg-card)] px-4 py-4 shadow-[var(--shadow)]"
    >
      <div className="flex items-start gap-3">
        {/* Contact avatar */}
        <InitialAvatar name={name} />

        <div className="min-w-0 flex-1">
          {/* Contact name */}
          <div className="flex items-start justify-between gap-3">
            <p className="truncate font-bold text-[var(--fg)]">
              {name}
            </p>

            {/* Similarity score */}
            {score !== undefined ? (
              <p className="t-caption shrink-0 font-medium">
                {Math.round(score * 100)}%
              </p>
            ) : null}
          </div>

          {/* Contact keywords */}
          {keywords.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {keywords.map(k => (
                <KeywordPill key={k} label={k} />
              ))}
            </div>
          ) : (
            <p className="t-caption">
              No keywords yet.
            </p>
          )}

          {/* Contact profile text */}
          {profileText ? (
            <p className="t-caption line-clamp-2">
              "{profileText}"
            </p>
          ) : null}
        </div>
      </div>
    </Link>
  )
}