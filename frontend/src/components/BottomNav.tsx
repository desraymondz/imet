import { NavLink, useNavigate } from 'react-router-dom'

export default function BottomNav() {
  const navigate = useNavigate()

  return (
    <nav className="bottom-nav" aria-label="Main">
      <div className="bottom-nav-bar">
        {/* Contacts button */}
        <NavLink
          to="/contacts"
          className={({ isActive }) =>
            `bottom-nav-item${isActive ? ' bottom-nav-item-active' : ''}`
          }
          end
        >
          <img src="/ui/users.svg" alt="" className="bottom-nav-icon" />
          <span>Contacts</span>
        </NavLink>

        {/* Empty grid cell reserved for the center FAB */}
        <div className="min-w-0" aria-hidden />

        {/* Recall button */}
        <NavLink
          to="/recall"
          className={({ isActive }) =>
            `bottom-nav-item${isActive ? ' bottom-nav-item-active' : ''}`
          }
          end
        >
          <img src="/ui/search.svg" alt="" className="bottom-nav-icon" />
          <span>Recall</span>
        </NavLink>
      </div>

      {/* Capture a new contact button */}
      <button
        type="button"
        className="bottom-nav-fab"
        aria-label="Add contact"
        onClick={() => navigate('/contacts/new')}
      >
        <img src="/ui/plus.svg" alt="" className="bottom-nav-icon bottom-nav-icon-fab" />
      </button>
    </nav>
  )
}
