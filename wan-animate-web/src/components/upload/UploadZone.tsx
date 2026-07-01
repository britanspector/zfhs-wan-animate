import { useRef, useState } from 'react'

interface UploadZoneProps {
  label: string
  accept: string
  previewUrl: string
  isVideo?: boolean
  isSample?: boolean
  onFile: (file: File | null) => void
}

export function UploadZone({
  label,
  accept,
  previewUrl,
  isVideo,
  isSample,
  onFile,
}: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [duration, setDuration] = useState<number | null>(null)

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0]
    if (!file) return
    if (isVideo && !file.type.startsWith('video/')) {
      alert('请选择有效的视频文件')
      return
    }
    onFile(file)
  }

  const openPicker = () => inputRef.current?.click()

  return (
    <div className="relative">
      <p className="mb-2 text-sm font-medium text-morandi-text">{label}</p>
      <div
        role="button"
        tabIndex={0}
        onClick={openPicker}
        onKeyDown={(e) => e.key === 'Enter' && openPicker()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          handleFiles(e.dataTransfer.files)
        }}
        className="group relative flex min-h-[140px] cursor-pointer items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-morandi-border bg-morandi-hover/50 transition hover:border-morandi-primary hover:bg-morandi-hover"
      >
        {isVideo ? (
          <video
            src={previewUrl}
            className="max-h-36 w-full object-contain"
            muted
            playsInline
            controls={!isSample}
            onClick={(e) => e.stopPropagation()}
            onLoadedMetadata={(e) => setDuration(Math.floor(e.currentTarget.duration))}
          />
        ) : (
          <img src={previewUrl} alt={label} className="max-h-36 w-full object-contain" />
        )}
        {isSample && (
          <span className="pointer-events-none absolute left-2 top-2 rounded-md bg-morandi-primary px-2 py-0.5 text-xs text-white">
            {isVideo ? '示例视频' : '示例图'}
          </span>
        )}
        {duration !== null && isVideo && (
          <span className="pointer-events-none absolute right-2 top-2 rounded-md bg-morandi-primary-dark/80 px-2 py-0.5 text-xs text-white">
            {duration}s
          </span>
        )}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center gap-2 bg-morandi-primary/30 opacity-0 transition group-hover:opacity-100">
          <span
            role="button"
            tabIndex={0}
            className="pointer-events-auto cursor-pointer rounded-lg bg-white px-3 py-1 text-sm text-morandi-primary shadow-sm"
            onClick={(e) => {
              e.stopPropagation()
              openPicker()
            }}
            onKeyDown={(e) => e.key === 'Enter' && openPicker()}
          >
            更换
          </span>
          {!isSample && (
            <button
              type="button"
              className="pointer-events-auto rounded-lg bg-morandi-danger px-3 py-1 text-sm text-white"
              onClick={(e) => {
                e.stopPropagation()
                onFile(null)
                setDuration(null)
              }}
            >
              删除
            </button>
          )}
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  )
}
