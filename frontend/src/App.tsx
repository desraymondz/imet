import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import LoginPage from './pages/Login.tsx'
import ContactsPage from './pages/Contacts.tsx'
import RecallPage from './pages/Recall.tsx'
import NewContactPage from './pages/NewContact.tsx'
import EditContactPage from './pages/EditContact.tsx'
import AppLayout from './layouts/AppLayout.tsx'
import Spinner from './components/Spinner.tsx'
import { api } from './libs/api.ts'

function RequireAuth({ children }: { children: ReactNode }) {
  // Check if the user is logged in by checking the JWT in the HttpOnly cookie

  const { isPending, isSuccess } = useQuery({
    // Cache key to drop a stale 401 after a successful sign in
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const response = await api.get('/auth/me')
      return response.data
    },
    retry: false,
    staleTime: 60_000,
  })

  // If the user is not logged in, show a loading spinner
  if (isPending) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner label="Checking session" />
      </div>
    )
  }

  // If the user is not logged in, redirect to the login page
  if (!isSuccess) {
    return <Navigate to="/login" replace />
  }

  // If the user is logged in, render the AppLayout and the nested page
  return children
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public: no session check */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected: RequireAuth checks /auth/me, then AppLayout (wave + nav) */}
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/contacts" element={<ContactsPage />} />
          <Route path="/contacts/new" element={<NewContactPage />} />
          <Route path="/contacts/:id/edit" element={<EditContactPage />} />
          <Route path="/recall" element={<RecallPage />} />
        </Route>

        {/* Unknown paths go to contacts and RequireAuth sends anonymous users to login */}
        <Route path="*" element={<Navigate to="/contacts" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App