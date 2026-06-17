type InitialAvatarProps = {
  name: string
  // avatar size (default is 12)
  sizeClassName?: string
  // extra classes (default is empty)
  className?: string
}

// Get the initials from a name
function initialsFromName(name: string) {
  const [a = '', b = ''] = name.trim().split(' ')
  return ((a[0] ?? '') + (b[0] ?? '')).toUpperCase() || '—'
}

export default function InitialAvatar({
  name,
  sizeClassName = 'size-12',
  className = '',
}: InitialAvatarProps) {
  return (
    <div
      className={[
        'grid shrink-0 place-items-center rounded-full text-[16px] font-bold text-white',
        'bg-[linear-gradient(135deg,var(--violet)_0%,var(--blue)_100%)]',
        sizeClassName,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      aria-hidden
    >
      {initialsFromName(name)}
    </div>
  )
}

