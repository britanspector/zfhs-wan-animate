import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children: ReactNode
}

const variants: Record<Variant, string> = {
  primary:
    'bg-morandi-primary hover:bg-morandi-primary-dark text-white shadow-sm disabled:opacity-50',
  secondary:
    'bg-morandi-surface border border-morandi-border text-morandi-text hover:bg-morandi-bg disabled:opacity-50',
  danger: 'bg-morandi-danger text-white hover:opacity-90 disabled:opacity-50',
  ghost: 'text-morandi-muted hover:text-morandi-text hover:bg-morandi-surface',
}

export function Button({ variant = 'primary', className = '', children, ...props }: ButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
