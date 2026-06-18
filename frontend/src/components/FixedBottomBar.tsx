// A fixed bottom bar that is always visible at the bottom of the screen

import type { ReactNode } from 'react'

type FixedBottomBarProps = {
  children: ReactNode
}

export default function FixedBottomBar({ children }: FixedBottomBarProps) {
  return (
    <div className="shrink-0 px-5 py-4">
      {children}
    </div>
  )
}
