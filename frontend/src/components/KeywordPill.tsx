type KeywordPillProps = {
  label: string
  className?: string
}

export default function KeywordPill({ label, className = '' }: KeywordPillProps) {
  return (
    <span
      className={[
        'rounded-full bg-[var(--violet-light)] px-3 py-1 text-[12px] font-semibold text-[var(--violet-deep)]',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {label}
    </span>
  )
}
