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
    <div className="flex h-full min-h-[320px] flex-col">
      <div className="mb-3 flex gap-2">
        <Button variant="danger" className="text-xs" disabled={!isGenerating} onClick={onStop}>
          停止
        </Button>
        <Button variant="secondary" className="text-xs" disabled={isGenerating} onClick={onHistory}>
          历史记录
        </Button>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center">
        {state === 'generating' && <ProgressCard progress={progress} />}

        {state === 'loadingResult' && (
          <div className="text-center">
            <div className="mx-auto mb-3 h-10 w-10 animate-spin rounded-full border-2 border-morandi-mist border-t-transparent" />
            <p className="text-morandi-muted">正在处理最终效果...</p>
          </div>
        )}

        {state === 'success' && videoUrl && (
          <ResultVideo url={videoUrl} elapsedSeconds={finalElapsed} />
        )}

        {state === 'error' && isError && (
          <div className="w-full rounded-xl bg-morandi-danger-bg p-4 text-sm text-morandi-text">
            <p className="font-medium text-morandi-danger">生成失败</p>
            <pre className="mt-2 whitespace-pre-wrap text-xs">{message}</pre>
          </div>
        )}

        {state === 'idle' && !videoUrl && (
          <div className="text-center text-morandi-muted">
            <div className="mx-auto mb-3 text-4xl opacity-40">✦</div>
            <p>暂无生成内容</p>
          </div>
        )}

        {message && !isError && state !== 'error' && (
          <p className="mt-4 text-center text-xs text-morandi-muted">{message}</p>
        )}
      </div>
    </div>
  )
}
