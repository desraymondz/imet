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
