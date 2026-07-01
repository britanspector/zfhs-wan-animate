interface ChipProps {
  label: string
  active: boolean
  onClick: () => void
}

export function Chip({ label, active, onClick }: ChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-1.5 text-sm transition ${
        active
          ? 'bg-morandi-primary text-white shadow-sm'
          : 'border border-morandi-border bg-white text-morandi-muted hover:border-morandi-primary hover:text-morandi-primary'
      }`}
    >
      {label}
    </button>
  )
}
