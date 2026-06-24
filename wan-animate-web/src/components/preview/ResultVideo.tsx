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
    <div className="relative mx-auto w-full max-w-[320px]">
      {elapsedSeconds !== undefined && elapsedSeconds > 0 && (
        <span className="absolute left-2 top-2 z-10 rounded-lg bg-morandi-sage/90 px-2 py-1 text-xs text-white">
          本地用时 {formatTime(elapsedSeconds)}
        </span>
      )}
      <video
        src={url}
        controls
        loop
        autoPlay
        muted
        playsInline
        className="aspect-[9/16] max-h-[480px] w-full rounded-xl bg-black/5 object-contain"
      />
    </div>
  )
}
