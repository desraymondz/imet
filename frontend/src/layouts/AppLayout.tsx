import { Outlet, useLocation } from 'react-router-dom'
import BottomNav from '../components/BottomNav'

export default function AppLayout() {
  // Get the current pathname
  const { pathname } = useLocation()
  // Hide the bottom nav on the new contact page
  const hideBottomNav = pathname === '/contacts/new'

  return (
    <div className="app-layout">
      {/* Background image */}
      <img
        className="app-layout-bg"
        src="/backgrounds/wave-bg.svg"
        alt=""
        aria-hidden
      />

      {/* Main content area */}
      <main
        className="app-layout-content"
        style={hideBottomNav ? { paddingBottom: 0 } : undefined}
      >
        {/* Outlet for the current route */}
        <Outlet />
      </main>

      {/* Bottom navigation */}
      {hideBottomNav ? null : <BottomNav />}
    </div>
  )
}
