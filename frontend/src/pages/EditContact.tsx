import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { api } from '../libs/api'

// UI components
import ConfirmDialog from '../components/ConfirmDialog'
import FixedBottomBar from '../components/FixedBottomBar'
import GradientButton from '../components/GradientButton'
import Spinner from '../components/Spinner'
import ReviewStep, { type ContactDraft } from '../components/new-contact/ReviewStep'
import type { Contact } from '../types/contact'

// Map a saved contact into the editable review draft shape
function contactToDraft(contact: Contact): ContactDraft {
  return {
    display_name: contact.display_name,
    email: contact.email,
    phone: contact.phone,
    company: contact.company,
    role: contact.role,
    location: contact.location,
    profile_text: contact.profile_text,
    keywords: contact.keywords,
  }
}

export default function EditContactPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Draft state
  const [draft, setDraft] = useState<ContactDraft | null>(null)
  const [error, setError] = useState('')
  // Whether the delete confirmation is open
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  // Parse the route param into a positive integer contact id
  const contactId = Number(id)
  const isValidId = Number.isInteger(contactId) && contactId > 0

  // Load the contact to edit
  const {
    data: contact,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['contacts', contactId],
    enabled: isValidId,
    queryFn: async () => {
      const response = await api.get(`/contacts/${contactId}`)
      return response.data as Contact
    },
  })

  // Prefill the form draft once the contact loads
  useEffect(() => {
    if (contact) setDraft(contactToDraft(contact))
  }, [contact])

  // Save the contact and return to the contacts list
  const saveMutation = useMutation({
    mutationFn: async (payload: ContactDraft) => {
      const response = await api.patch(`/contacts/${contactId}`, payload)
      return response.data as Contact
    },
    onSuccess: async () => {
      // Refetch contacts to update the contact list
      await queryClient.invalidateQueries({ queryKey: ['contacts'] })
      navigate('/contacts')
    },
  })

  // Delete the contact and return to the contacts list
  const deleteMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/contacts/${contactId}`)
    },
    onSuccess: async () => {
      // Drop the deleted contact's cached detail, then refetch the contact list
      queryClient.removeQueries({ queryKey: ['contacts', contactId] })
      await queryClient.invalidateQueries({ queryKey: ['contacts'] })
      navigate('/contacts')
    },
  })

  // Update one of the fields in the review draft
  function updateDraft(field: keyof ContactDraft, value: string | string[] | null) {
    setDraft(prev => (prev ? { ...prev, [field]: value } : prev))
  }

  // Close the edit contact flow by navigating back to the contacts page
  function handleClose() {
    navigate('/contacts')
  }

  // Save the contact
  async function handleSave() {
    if (!draft) return

    setError('')
    const name = (draft.display_name ?? '').trim()

    // If no name is provided, set the error message and return
    if (!name) {
      setError('Add a name before saving.')
      return
    }

    try {
      // Save the contact draft
      await saveMutation.mutateAsync({
        ...draft,
        display_name: name,
        keywords: (draft.keywords ?? []).filter(Boolean),
      })
    } catch {
      // Set the error message
      setError('Could not save this contact. Please try again.')
    }
  }

  // Delete the contact once the user confirms
  async function handleDelete() {
    setError('')

    try {
      await deleteMutation.mutateAsync()
    } catch {
      // Keep the user on the form so nothing they typed is lost
      setConfirmingDelete(false)
      setError('Could not delete this contact. Please try again.')
    }
  }

  // Invalid id or contact not found page
  if (!isValidId || isError) {
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <header className="px-5 pt-5">
          <CloseButton onClose={handleClose} />
        </header>
        <p className="flex flex-1 items-center justify-center px-5 text-center text-xl text-[var(--fg-2)]">
          Contact not found.
        </p>
      </div>
    )
  }

  // Wait until the contact is loaded and the draft form is prefilled
  if (isLoading || !draft) {
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <header className="px-5 pt-5">
          <CloseButton onClose={handleClose} />
        </header>
        <Spinner label="Loading contact" />
      </div>
    )
  }

  return (
    // Anchor the confirm dialog to the page, not the app shell
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
      {/* Close and delete actions */}
      <header className="flex items-center justify-between px-5 pt-5">
        <CloseButton onClose={handleClose} />

        <button
          type="button"
          onClick={() => setConfirmingDelete(true)}
          disabled={deleteMutation.isPending}
          className="flex size-10 items-center justify-center rounded-full text-[var(--danger)] disabled:opacity-50"
          aria-label="Delete contact"
        >
          <Trash2 className="size-5" aria-hidden />
        </button>
      </header>

      {/* Review form */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-4 pt-5">
        {/* Remount when contact id changes so the draft form is prefilled again */}
        <ReviewStep
          key={contactId}
          title="Edit contact"
          draft={draft}
          onChange={updateDraft}
          error={error}
        />
      </div>

      {/* Bottom save action */}
      <FixedBottomBar>
        {/* Only let the user save if the backend is done saving */}
        <GradientButton onClick={handleSave} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? 'Saving…' : 'Save changes'}
        </GradientButton>
      </FixedBottomBar>

      {/* Confirm delete dialog */}
      {confirmingDelete ? (
        <ConfirmDialog
          title="Delete contact?"
          message={`${(draft.display_name ?? '').trim() || 'This contact'} will be removed for good. This cannot be undone.`}
          confirmLabel={deleteMutation.isPending ? 'Deleting…' : 'Delete'}
          pending={deleteMutation.isPending}
          onConfirm={handleDelete}
          onCancel={() => setConfirmingDelete(false)}
        />
      ) : null}
    </div>
  )
}

// Close button used in the edit contact header
function CloseButton({ onClose }: { onClose: () => void }) {
  return (
    <button
      type="button"
      onClick={onClose}
      className="flex size-10 items-center justify-center rounded-full text-[var(--fg-2)]"
      aria-label="Close"
    >
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
  )
}