import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import LoginPage from './pages/Login.tsx'
import ContactsPage from './pages/Contacts.tsx'
import RecallPage from './pages/Recall.tsx'
import NewContactPage from './pages/NewContact.tsx'
import AppLayout from './layouts/AppLayout.tsx'

function RequireAuth({ children }: { children: ReactNode }) {
  // Redirect to login if no JWT in localStorage
  // TODO: change to HTTP-only cookie
  const token = localStorage.getItem('token')
  return token ? children : <Navigate to="/login" replace />
}

function App() {
  const token = localStorage.getItem('token')

  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Authenticated routes with wave background and bottom nav */}
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/contacts" element={<ContactsPage />} />
          <Route path="/contacts/new" element={<NewContactPage />} />
          <Route path="/recall" element={<RecallPage />} />
        </Route>

        {/* Redirects to login or contacts based on auth status */}
        <Route path="*" element={<Navigate to={token ? '/contacts' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App