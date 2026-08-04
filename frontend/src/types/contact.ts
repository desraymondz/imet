export interface Contact {
  id: number
  display_name: string | null
  email: string | null
  company: string | null
  role: string | null
  profile_text: string | null
  keywords: string[] | null
  created_at: string
}

export interface RecallResult {
  contact: Contact
  score: number
}

// Status of a recall search (success, out of scope, no matches, error)
export type RecallStatus = 'ok' | 'out_of_scope' | 'no_matches' | 'error'

export interface RecallSearchResponse {
  status: RecallStatus
  results: RecallResult[]
}
