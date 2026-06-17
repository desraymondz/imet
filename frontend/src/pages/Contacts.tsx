import { useQuery } from '@tanstack/react-query'
import { api } from '../libs/api'
import InitialAvatar from '../components/InitialAvatar'
import KeywordPill from '../components/KeywordPill'

interface Contact {
  id: number
  display_name: string | null
  email: string | null
  company: string | null
  role: string | null
  profile_text: string | null
  keywords: string[] | null
  created_at: string
}

export default function ContactsPage() {
  // Get contacts from the API
  const { data: contacts, isLoading } = useQuery({
    queryKey: ['contacts'],
    queryFn: async () => {
      const response = await api.get('/contacts/')
      return response.data as Contact[]
    },
  })

  // Loading state
  if (isLoading) return <p className="p-4">Loading...</p>

  // Get the total number of contacts
  const totalCount = (contacts ?? []).length

  return (
    <div className="mx-auto w-full max-w-md px-5 pb-4 pt-6">
      <h1>Contacts</h1>
      {/* Main content */}
      <div className="flex items-start justify-between gap-4">
        {/* Total contact count */}
        <p>{totalCount} People</p>
      </div>

      {/* No contacts found state */}
      {(contacts ?? []).length === 0 ? (
        <p className="mt-6 text-center text-[14px] text-[var(--fg-2)]">
          No contacts yet.
        </p>
      ) : (
        <ul className="mt-5 space-y-4">
          {(contacts ?? []).map(contact => {
            // Get the contact name
            const name = (contact.display_name ?? '').trim() || '—'
            // Get the contact profile text
            const profileText = (contact.profile_text ?? '').trim() || 'No profile text yet.'
            // Get the contact keywords
            const keywords = (contact.keywords ?? []).filter(Boolean).slice(0, 6)

            return (
              <li key={contact.id}>
                <div className="rounded-[22px] border border-white/40 bg-white/70 px-4 py-4 shadow-[var(--shadow)] backdrop-blur">
                  <div className="flex items-start gap-3">
                    {/* Contact avatar */}
                    <InitialAvatar name={name} />

                    <div className="min-w-0 flex-1">
                      {/* Contact name */}
                      <div className="flex items-start justify-between gap-3">
                        <p className="truncate text-[18px] font-bold text-[var(--fg)]">
                          {name}
                        </p>
                      </div>

                      {/* Contact keywords */}
                      {keywords.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {keywords.map(k => (
                            <KeywordPill key={k} label={k} />
                          ))}
                        </div>
                      ) : (
                        <p className="text-[13px] text-[var(--fg-2)]">
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
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}