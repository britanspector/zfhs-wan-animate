import { useEffect, useRef, useState, type ReactNode } from 'react'

export function TwoColumnLayout({ left, right }: { left: ReactNode; right: ReactNode }) {
  const leftRef = useRef<HTMLDivElement>(null)
  const [rightHeight, setRightHeight] = useState<number>()

  useEffect(() => {
    const el = leftRef.current
    if (!el) return

    const sync = () => {
      if (window.matchMedia('(min-width: 1024px)').matches) {
        setRightHeight(el.offsetHeight)
      } else {
        setRightHeight(undefined)
      }
    }

    const observer = new ResizeObserver(sync)
    observer.observe(el)
    window.addEventListener('resize', sync)
    sync()

    return () => {
      observer.disconnect()
      window.removeEventListener('resize', sync)
    }
  }, [])

  return (
    <div className="mx-auto grid max-w-7xl gap-3 lg:grid-cols-[minmax(0,0.9fr)_minmax(460px,550px)] lg:items-start">
      <div ref={leftRef} className="flex min-w-0 flex-col gap-3">
        {left}
      </div>

      <div
        className="card flex min-h-0 min-w-0 flex-col overflow-hidden lg:max-w-[550px] lg:justify-self-end"
        style={rightHeight ? { height: rightHeight } : undefined}
      >
        {right}
      </div>
    </div>
  )
}
