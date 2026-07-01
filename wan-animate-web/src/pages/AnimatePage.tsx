import { UploadZone } from '../components/upload/UploadZone'
import { ControlPanel } from '../components/controls/ControlPanel'
import { WorkflowPresetSelector } from '../components/controls/WorkflowPresetSelector'
import { TunableParamsPanel } from '../components/controls/TunableParamsPanel'
import { PreviewPanel } from '../components/preview/PreviewPanel'
import { Header } from '../components/layout/Header'
import { TwoColumnLayout } from '../components/layout/TwoColumnLayout'
import { Button } from '../components/common/Button'
import { useWorkflowConfig } from '../hooks/useWorkflowConfig'
import { useGpuInfo } from '../hooks/useGpuInfo'
import { useComfyStatus } from '../hooks/useComfyStatus'
import { useGenerate } from '../hooks/useGenerate'
import { defaultTunablesForVariant } from '../types/workflow'

export function AnimatePage() {
  const { config, loading } = useWorkflowConfig()
  const gpu = useGpuInfo()
  const { isRunning, starting, startComfy } = useComfyStatus()
  const gen = useGenerate(config)

  if (loading) {
    return <div className="p-8 text-center text-morandi-muted">加载配置...</div>
  }

  const hasGpu = gpu?.hasGPU ?? true
  const isGenerating = gen.previewState === 'generating'

  let ctaLabel = '开始执行动画迁移'
  let ctaDisabled = !gen.canGenerate || isGenerating
  let ctaAction: () => void = () => {
    void gen.generate()
  }

  if (!hasGpu) {
    ctaLabel = '无卡模式不可运行'
    ctaDisabled = true
  } else if (!isRunning) {
    ctaLabel = starting ? 'ComfyUI 启动中...' : '⚡ 启动 ComfyUI'
    ctaAction = () => {
      void startComfy()
    }
    ctaDisabled = starting
  } else if (isGenerating) {
    ctaLabel = '角色融合与动画合成中...'
    ctaDisabled = true
  }

  return (
    <div className="px-4 py-3">
      <Header />
      <TwoColumnLayout
        left={
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              <UploadZone
                label="角色图像"
                accept="image/*"
                previewUrl={gen.imagePreview}
                isSample={gen.imageSource === 'sample'}
                onFile={gen.setImage}
              />
              <UploadZone
                label="动作视频"
                accept="video/*"
                previewUrl={gen.videoPreview}
                isVideo
                isSample={gen.videoSource === 'sample'}
                onFile={gen.setVideo}
              />
            </div>
            <WorkflowPresetSelector
              variants={config.variants ?? []}
              selected={gen.workflowVariant}
              disabled={isGenerating}
              onChange={gen.selectWorkflowVariant}
            />
            <TunableParamsPanel
              schema={config.tunables ?? []}
              values={gen.tunables}
              variantDefaults={defaultTunablesForVariant(config, gen.workflowVariant)}
              disabled={isGenerating}
              onChange={gen.setTunable}
            />
            <ControlPanel
              width={gen.width}
              height={gen.height}
              seconds={gen.seconds}
              durationOptions={config.duration_options}
              onWidthChange={gen.setWidth}
              onHeightChange={gen.setHeight}
              onSecondsChange={gen.setSeconds}
              onReset={gen.resetDefaults}
            />
            <Button
              className="w-full py-2.5 text-base"
              disabled={ctaDisabled}
              onClick={ctaAction}
            >
              {ctaLabel}
            </Button>
          </>
        }
        right={
          <PreviewPanel
            state={gen.previewState}
            message={gen.message}
            videoUrl={gen.videoUrl}
            finalElapsed={gen.finalElapsed}
            progress={gen.progress}
            isGenerating={isGenerating}
            onStop={gen.stopGeneration}
            onHistory={gen.loadLatestFromHistory}
          />
        }
      />
    </div>
  )
}
