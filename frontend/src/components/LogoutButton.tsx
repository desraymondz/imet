import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { LogOut } from 'lucide-react'
import { api } from '../libs/api'

export default function LogoutButton() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  async function handleLogout() {
    try {
      // Clear the HTTP-only session cookie
      await api.post('/auth/logout')
    } finally {
      // Drop cached session/contacts so the next user does not see them
      queryClient.clear()
      navigate('/login', { replace: true })
    }
  }

  return (
    <button
      type="button"
      className="flex shrink-0 items-center gap-1.5 text-[14px] font-medium text-[var(--danger)]"
      onClick={() => void handleLogout()}
    >
      <LogOut className="size-4" aria-hidden />
      Log out
    </button>
  )
}
