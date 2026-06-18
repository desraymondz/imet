// Gradient button block

type GradientButtonProps = {
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
  type?: 'button' | 'submit'
}

export default function GradientButton({ children, onClick, disabled, type = 'button' }: GradientButtonProps) {
  return (
    <button
      type={type}
      className="btn btn--primary btn--block"
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}