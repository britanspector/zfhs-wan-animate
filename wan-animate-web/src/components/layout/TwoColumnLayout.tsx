import type { ReactNode } from 'react'

export function TwoColumnLayout({ left, right }: { left: ReactNode; right: ReactNode }) {
  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)] lg:items-start">
      <div className="flex flex-col gap-4">{left}</div>
      <div className="rounded-2xl bg-morandi-surface p-4 shadow-sm ring-1 ring-morandi-border/60 lg:max-w-[360px] lg:justify-self-end">
        {right}
      </div>
    </div>
  )
}
