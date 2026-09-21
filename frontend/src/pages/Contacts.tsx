import { useQuery } from '@tanstack/react-query'
import { api } from '../libs/api'
import ContactCard from '../components/ContactCard'
import LogoutButton from '../components/LogoutButton'
import Spinner from '../components/Spinner'
import type { Contact } from '../types/contact'

export default function ContactsPage() {
  // Get contacts from the API
  const { data: contacts, isLoading } = useQuery({
    queryKey: ['contacts'],
    queryFn: async () => {
      const response = await api.get('/contacts/')
      return response.data as Contact[]
    },
  })

  // Get the total number of contacts
  const totalCount = (contacts ?? []).length

  return (
    <div className="mx-auto flex min-h-full w-full max-w-md flex-col px-5 pb-4 pt-6">
      <div className="flex items-center justify-between gap-4">
        <h1>Contacts</h1>
        <LogoutButton />
      </div>

      {isLoading ? (
        <Spinner label="Loading contacts" />
      ) : (
        <>
          {/* Main content */}
          <div className="flex items-start justify-between gap-4">
            {/* Total contact count */}
            <p>{totalCount} People</p>
          </div>

          {/* No contacts found state */}
          {totalCount === 0 ? (
            <p className="mt-6 text-center text-[14px] text-[var(--fg-2)]">
              No contacts yet.
            </p>
          ) : (
            <ul className="mt-5 space-y-4">
              {(contacts ?? []).map(contact => (
                <li key={contact.id}>
                  <ContactCard contact={contact} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}