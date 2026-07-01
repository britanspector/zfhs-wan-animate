import type { DurationOption } from '../../types/workflow'
import { Chip } from '../common/Chip'
import { Button } from '../common/Button'
import { InfoBanner } from './InfoBanner'

interface ControlPanelProps {
  width: number
  height: number
  seconds: number
  durationOptions: DurationOption[]
  onWidthChange: (v: number) => void
  onHeightChange: (v: number) => void
  onSecondsChange: (s: number) => void
  onReset: () => void
}

export function ControlPanel({
  width,
  height,
  seconds,
  durationOptions,
  onWidthChange,
  onHeightChange,
  onSecondsChange,
  onReset,
}: ControlPanelProps) {
  const isSafeSize = width === 468 && height === 832

  return (
    <div className="card">
      <InfoBanner />
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="text-morandi-muted">视频宽度（节点 1001）</span>
          <input
            type="number"
            value={width}
            onChange={(e) => onWidthChange(Number(e.target.value))}
            min={468}
            max={468}
            step={1}
            className="mt-1 w-full rounded-lg border border-morandi-border bg-white px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="text-morandi-muted">视频高度（节点 1002）</span>
          <input
            type="number"
            value={height}
            onChange={(e) => onHeightChange(Number(e.target.value))}
            min={832}
            max={832}
            step={1}
            className="mt-1 w-full rounded-lg border border-morandi-border bg-white px-3 py-2"
          />
        </label>
      </div>
      {!isSafeSize && (
        <p className="mt-2 text-xs text-morandi-danger">
          当前工作流的姿态检测节点仅验证过 468 x 832，其他尺寸容易触发 ONNX 异常。
        </p>
      )}
      <div className="mt-4">
        <p className="mb-2 text-sm text-morandi-muted">截取时长（节点 1003，30 帧/秒）</p>
        <div className="flex flex-wrap gap-2">
          {durationOptions.map((opt) => (
            <Chip
              key={opt.seconds}
              label={opt.label}
              active={seconds === opt.seconds}
              onClick={() => onSecondsChange(opt.seconds)}
            />
          ))}
        </div>
      </div>
      <Button variant="secondary" className="mt-4 w-full" onClick={onReset}>
        恢复默认尺寸与截取时长
      </Button>
    </div>
  )
}
