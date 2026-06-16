import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/Login.tsx'
import ContactsPage from './pages/Contacts.tsx'

function App() {
  const token = localStorage.getItem('token')

  return (
    // Set up the browser router for React Router
    <BrowserRouter>
      {/* Set up the routes*/}
      <Routes>
        {/* Login page */}
        <Route 
          path="/login" 
          element={<LoginPage />} 
        />

        {/* Contacts page */}
        <Route
          path="/contacts"
          element={token ? <ContactsPage /> : <Navigate to="/login" />}
        />
        
        {/* Redirect to login or contacts page based on the authentication status */}
        <Route path="*" element={<Navigate to={token ? "/contacts" : "/login"} />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App