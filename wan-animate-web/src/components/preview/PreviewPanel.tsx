import type { PreviewState } from '../../types/workflow'
import type { ProgressState } from '../../types/workflow'
import { Button } from '../common/Button'
import { ProgressCard } from './ProgressCard'
import { ResultVideo } from './ResultVideo'

interface PreviewPanelProps {
  state: PreviewState
  message: string
  videoUrl: string | null
  finalElapsed: number
  progress: ProgressState
  isGenerating: boolean
  onStop: () => void
  onHistory: () => void
}

export function PreviewPanel({
  state,
  message,
  videoUrl,
  finalElapsed,
  progress,
  isGenerating,
  onStop,
  onHistory,
}: PreviewPanelProps) {
  const isError = message.includes('❌')

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-2 flex shrink-0 gap-2">
        <Button variant="danger" className="text-xs" disabled={!isGenerating} onClick={onStop}>
          停止
        </Button>
        <Button variant="secondary" className="text-xs" disabled={isGenerating} onClick={onHistory}>
          历史记录
        </Button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {state === 'generating' && (
          <div className="flex flex-1 items-center justify-center overflow-y-auto">
            <ProgressCard progress={progress} />
          </div>
        )}

        {state === 'loadingResult' && (
          <div className="flex flex-1 items-center justify-center text-center">
            <div>
              <div className="mx-auto mb-3 h-10 w-10 animate-spin rounded-full border-2 border-morandi-primary border-t-transparent" />
              <p className="text-morandi-muted">正在处理最终效果...</p>
            </div>
          </div>
        )}

        {state === 'success' && videoUrl && (
          <div className="flex min-h-0 flex-1 overflow-hidden">
            <ResultVideo url={videoUrl} elapsedSeconds={finalElapsed} />
          </div>
        )}

        {state === 'error' && isError && (
          <div className="flex flex-1 items-center justify-center p-2">
            <div className="w-full rounded-xl bg-morandi-danger-bg p-4 text-sm text-morandi-text">
              <p className="font-medium text-morandi-danger">生成失败</p>
              <pre className="mt-2 whitespace-pre-wrap text-xs">{message}</pre>
            </div>
          </div>
        )}

        {state === 'idle' && !videoUrl && (
          <div className="flex flex-1 items-center justify-center text-center text-morandi-muted">
            <div>
              <div className="mx-auto mb-3 text-4xl text-morandi-primary-light">✦</div>
              <p>暂无生成内容</p>
            </div>
          </div>
        )}

        {message && !isError && state !== 'error' && (
          <p className="mt-2 shrink-0 text-center text-xs text-morandi-muted">{message}</p>
        )}
      </div>
    </div>
  )
}
