import { Outlet } from 'react-router-dom'
import BottomNav from '../components/BottomNav'

export default function AppLayout() {
    return (
        <div className="app-layout">
            <img
                className="app-layout-bg"
                src="/backgrounds/wave-bg.svg"
                alt=""
                aria-hidden
            />
            <main className="app-layout-content">
                <Outlet />
            </main>
            <BottomNav />
        </div>
    )
}
