// Neutral button block

type NeutralButtonProps = {
  label: string
  onClick?: () => void
}

export default function NeutralButton({ label, onClick }: NeutralButtonProps) {
  return (
    <button
      type="button"
      className="btn btn--neutral btn--block"
      onClick={onClick}
    >
      {label}
    </button>
  )
}
