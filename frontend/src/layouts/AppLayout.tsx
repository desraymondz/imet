import { Outlet, useLocation } from 'react-router-dom'
import BottomNav from '../components/BottomNav'

export default function AppLayout() {
  // Get the current pathname
  const { pathname } = useLocation()
  // Hide the bottom nav on create/edit contact (fullscreen forms)
  const hideBottomNav =
    pathname === '/contacts/new' || /^\/contacts\/[^/]+\/edit$/.test(pathname)

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
        className={
          hideBottomNav
            ? 'app-layout-content app-layout-content--standalone'
            : 'app-layout-content'
        }
      >
        {/* Outlet for the current route */}
        <Outlet />
      </main>

      {/* Bottom navigation */}
      {hideBottomNav ? null : <BottomNav />}
    </div>
  )
}
