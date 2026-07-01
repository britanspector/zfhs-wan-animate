interface ResultVideoProps {
  url: string
  elapsedSeconds?: number
}

function formatTime(sec: number) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function ResultVideo({ url, elapsedSeconds }: ResultVideoProps) {
  return (
    <div className="relative h-full min-h-0 w-full overflow-hidden">
      {elapsedSeconds !== undefined && elapsedSeconds > 0 && (
        <span className="absolute left-2 top-2 z-10 rounded-lg bg-morandi-primary px-2 py-1 text-xs text-white">
          本地用时 {formatTime(elapsedSeconds)}
        </span>
      )}
      <div className="flex h-full min-h-0 items-center justify-center">
        <video
          src={url}
          controls
          loop
          autoPlay
          muted
          playsInline
          className="block h-full w-auto max-w-full rounded-xl bg-black/5 object-contain"
        />
      </div>
    </div>
  )
}
