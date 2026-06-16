import { useQuery } from '@tanstack/react-query'
import { api } from '../libs/api'

interface Contact {
    id: number
    display_name: string | null
    email: string | null
    company: string | null
    role: string | null
    profile_text: string | null
    created_at: string
}

export default function ContactsPage() {
    // Fetch the contacts from the API
    const { data: contacts, isLoading } = useQuery({
        queryKey: ['contacts'],
        queryFn: async () => {
            const response = await api.get('/contacts/')
            return response.data as Contact[]
        },
    })

    // Display a loading message while the contacts are being fetched
    if (isLoading) return <p className="p-4">Loading...</p>

    return (
        <div>
            <h1>Contacts</h1>
            {contacts?.length === 0 && (
                <p>No contacts yet.</p>
            )}
            <ul>
                {contacts?.map(contact => (
                    <li key={contact.id}>
                        <p>{contact.display_name ?? '—'}</p>
                        <p>{contact.company} · {contact.role}</p>
                        <p>{contact.email}</p>
                    </li>
                ))}
            </ul>
        </div>
    )
}