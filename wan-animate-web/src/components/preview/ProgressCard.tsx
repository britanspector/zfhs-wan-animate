import type { ProgressState } from '../../types/workflow'

function formatTime(sec: number) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function ProgressCard({ progress }: { progress: ProgressState }) {
  return (
    <div className="flex flex-col items-center gap-4 py-8">
      <div className="h-12 w-12 animate-pulse rounded-xl bg-morandi-mist/40" />
      <p className="text-lg font-medium text-morandi-text">角色融合与动画合成中...</p>
      <p className="text-sm text-morandi-muted">{formatTime(progress.elapsedSeconds)}</p>
      {progress.currentNodeName && (
        <p className="text-xs text-morandi-muted">{progress.currentNodeName}</p>
      )}
      <div className="w-full max-w-md space-y-3">
        <div>
          <div className="mb-1 flex justify-between text-xs text-morandi-muted">
            <span>整体进度</span>
            <span>{Math.round(progress.workflowProgress)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-morandi-border">
            <div
              className="h-full rounded-full bg-gradient-to-r from-morandi-mist to-morandi-primary shimmer-bar"
              style={{ width: `${progress.workflowProgress}%` }}
            />
          </div>
        </div>
        <div>
          <div className="mb-1 flex justify-between text-xs text-morandi-muted">
            <span>当前节点</span>
            <span>{Math.round(progress.nodeProgress)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-morandi-border">
            <div
              className="h-full rounded-full bg-morandi-sage transition-all"
              style={{ width: `${progress.nodeProgress}%` }}
            />
          </div>
        </div>
        {progress.totalNodes > 0 && (
          <p className="text-center text-xs text-morandi-muted">
            已执行节点 {progress.executedNodes} / {progress.totalNodes}
          </p>
        )}
      </div>
    </div>
  )
}
