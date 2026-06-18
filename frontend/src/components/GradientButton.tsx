// A gradient button block

type GradientButtonProps = {
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
}

export default function GradientButton({ children, onClick, disabled }: GradientButtonProps) {
  return (
    <button
      type="button"
      className="btn btn--primary btn--block"
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}