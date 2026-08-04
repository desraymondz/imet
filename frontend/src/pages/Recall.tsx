import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../libs/api'
import ContactCard from '../components/ContactCard'
import GradientButton from '../components/GradientButton'
import type { RecallResult, RecallSearchResponse, RecallStatus } from '../types/contact'

function messageForRecallStatus(status: RecallStatus | null): string {
  switch (status) {
    case 'out_of_scope':
      return 'That does not look like a contact recall question.'
    case 'no_matches':
      return 'No matches found.'
    case 'error':
      return 'Something went wrong while searching.'
    default:
      return ''
  }
}

export default function RecallPage() {
  // Search query state
  const [query, setQuery] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [results, setResults] = useState<RecallResult[]>([])
  const [recallStatus, setRecallStatus] = useState<RecallStatus | null>(null)
  const [error, setError] = useState('')

  // Search contacts from the API
  // Reference: https://tanstack.com/query/latest/docs/framework/react/reference/useMutation
  const searchMutation = useMutation({
    mutationFn: async (searchQuery: string) => {
      const response = await api.post('/recall/search', { query: searchQuery })
      return response.data as RecallSearchResponse
    },
    onSuccess: data => {
      setResults(data.results)
      setRecallStatus(data.status)
      setHasSearched(true)
    },
  })

  // Handle search form submission
  function handleSearch() {
    setError('')
    const trimmed = query.trim()

    // If the query is empty, set the error message and return
    if (!trimmed) {
      setError('Enter a question to search.')
      return
    }

    // Reset the search state before calling the mutation
    setHasSearched(false)
    setResults([])
    setRecallStatus(null)

    // Call the search mutation
    searchMutation.mutate(trimmed, {
      onError: () => {
        setError('Could not search. Please try again.')
        setRecallStatus('error')
        setHasSearched(true)
      },
    })
  }

  // Loading state
  if (searchMutation.isPending) return <p className="p-4">Searching...</p>

  // Get the status message for the results area
  const statusMessage = !hasSearched
    ? 'Ask about someone you met.'
    : !error && results.length === 0
      ? messageForRecallStatus(recallStatus) || 'No matches found.'
      : ''

  return (
    <div className="mx-auto flex min-h-full w-full max-w-md flex-col px-5 pb-4 pt-6">
      <h1>Recall</h1>
      {/* Main content */}
      <form
        className="mt-4 flex flex-col gap-3"
        onSubmit={e => {
          e.preventDefault()
          handleSearch()
        }}
      >
        {/* Search input */}
        <label className="field">
          <span className="sr-only">Search query</span>
          <input
            type="text"
            className="input"
            placeholder="Who did I meet that likes hiking?"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </label>

        {/* Error message */}
        {error ? (
          <p className="text-error">{error}</p>
        ) : null}

        {/* Search button */}
        <GradientButton type="submit">Search</GradientButton>
      </form>


      {/* Results area */}
      {results.length > 0 ? (
        <ul className="mt-5 space-y-4">
          {results.map(result => (
            <li key={result.contact.id}>
              <ContactCard contact={result.contact} score={result.score} />
            </li>
          ))}
        </ul>
      ) : statusMessage ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="t-caption text-center">{statusMessage}</p>
        </div>
      ) : null}
    </div>
  )
}