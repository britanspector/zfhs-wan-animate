import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { buildViewUrl } from '../api/endpoints'
import { basenameFromPath, SAMPLE_IMAGE, SAMPLE_VIDEO } from '../constants/samples'
import type { JobRecord, WorkflowResultItem } from '../types/api'
import type { PreviewState, WorkflowConfig } from '../types/workflow'
import { defaultTunablesForVariant } from '../types/workflow'
import { useComfyProgress } from './useComfyProgress'
import { formatWorkflowError } from '../utils/formatError'
import { normalizeMediaUrl } from '../utils/normalizeMediaUrl'

const SAFE_WIDTH = 468
const SAFE_HEIGHT = 832

export type MediaSource = 'sample' | 'restored' | 'upload'

function randomClientId() {
  // iframe / 部分 WebView 可能没有 crypto.randomUUID（非安全上下文或实现不全）
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '')
  }
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const buf = new Uint8Array(16)
    crypto.getRandomValues(buf)
    return Array.from(buf, (b) => b.toString(16).padStart(2, '0')).join('')
  }
  return `c${Date.now().toString(16)}${Math.random().toString(16).slice(2, 14)}`
}

function normalizeDimension(value: number, fallback: number) {
  return Number.isFinite(value) && value > 0 ? Math.round(value) : fallback
}

function pollTimeoutMs(seconds: number) {
  return Math.max(20 * 60 * 1000, seconds * 45 * 1000 + 8 * 60 * 1000)
}

function sampleNamesFromConfig(config: WorkflowConfig) {
  return {
    image: basenameFromPath(config.samples.image, SAMPLE_IMAGE),
    video: basenameFromPath(config.samples.video, SAMPLE_VIDEO),
  }
}

function sampleImageUrl(config: WorkflowConfig) {
  return config.samples.image_preview_url ?? buildViewUrl(SAMPLE_IMAGE, 'input')
}

function sampleVideoUrl(config: WorkflowConfig) {
  return config.samples.video_preview_url ?? buildViewUrl(SAMPLE_VIDEO, 'input')
}

function pickRestoreJob(jobs: JobRecord[]): JobRecord | undefined {
  return (
    jobs.find((j) => j.status === 'completed' && (j.video || j.image)) ??
    jobs.find((j) => j.video || j.image)
  )
}

function jobVideoName(job: JobRecord): string | undefined {
  return job.video ?? (job.input_values?.['997:video'] as string | undefined)
}

function jobImageName(job: JobRecord): string | undefined {
  return job.image ?? (job.input_values?.['57:image'] as string | undefined)
}

function applyResult(
  res: { pending?: boolean; error?: string; results?: WorkflowResultItem[] },
  startMs: number,
  setPreviewState: (s: PreviewState) => void,
  setMessage: (m: string) => void,
  setVideoUrl: (u: string | null) => void,
  setFinalElapsed: (n: number) => void,
) {
  if (res.pending) return false
  if (res.error) {
    setPreviewState('error')
    setMessage(`❌ ${formatWorkflowError(res.error)}`)
    return true
  }
  if (res.results?.length) {
    setPreviewState('loadingResult')
    setVideoUrl(normalizeMediaUrl(res.results[0].url))
    setFinalElapsed(Math.floor((Date.now() - startMs) / 1000))
    setPreviewState('success')
    setMessage('生成完成')
    return true
  }
  setPreviewState('error')
  setMessage('❌ 未找到输出视频')
  return true
}

export function useGenerate(config: WorkflowConfig, options?: { warmupReady?: boolean }) {
  const warmupReady = options?.warmupReady ?? true
  const initialSamples = sampleNamesFromConfig(config)
  const [previewState, setPreviewState] = useState<PreviewState>('idle')
  const [message, setMessage] = useState('')
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [finalElapsed, setFinalElapsed] = useState(0)
  const [promptId, setPromptId] = useState<string | null>(null)
  const abortRef = useRef(false)
  const restoredRef = useRef(false)
  const historyCheckedRef = useRef(false)
  const {
    progress,
    prepareConnection,
    disconnect,
    reset,
    bindPrompt,
    takeDiagnosticLog,
    startElapsed,
  } = useComfyProgress()

  const [width, setWidth] = useState(config.defaults.width)
  const [height, setHeight] = useState(config.defaults.height)
  const [seconds, setSeconds] = useState(config.defaults.seconds)

  const [imageFile, setImageFile] = useState<File | null>(null)
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState(sampleImageUrl(config))
  const [videoPreview, setVideoPreview] = useState(sampleVideoUrl(config))
  const [imageName, setImageName] = useState(initialSamples.image)
  const [videoName, setVideoName] = useState(initialSamples.video)
  const [imageSource, setImageSource] = useState<MediaSource>('sample')
  const [videoSource, setVideoSource] = useState<MediaSource>('sample')
  const [workflowVariant, setWorkflowVariant] = useState(
    config.default_workflow_variant || 'v4',
  )
  const [tunables, setTunables] = useState<Record<string, string | number | boolean>>(() =>
    defaultTunablesForVariant(config, config.default_workflow_variant || 'v4'),
  )

  const applySampleDefaults = useCallback(() => {
    const names = sampleNamesFromConfig(config)
    setImageName(names.image)
    setVideoName(names.video)
    setImagePreview(sampleImageUrl(config))
    setVideoPreview(sampleVideoUrl(config))
    setImageSource('sample')
    setVideoSource('sample')
    setImageFile(null)
    setVideoFile(null)
  }, [config])

  useEffect(() => {
    setWorkflowVariant(config.default_workflow_variant || 'v4')
    setTunables(defaultTunablesForVariant(config, config.default_workflow_variant || 'v4'))
    if (!historyCheckedRef.current) return
    if (imageSource === 'sample' && !imageFile) {
      const names = sampleNamesFromConfig(config)
      setImageName(names.image)
      setImagePreview(sampleImageUrl(config))
    }
    if (videoSource === 'sample' && !videoFile) {
      const names = sampleNamesFromConfig(config)
      setVideoName(names.video)
      setVideoPreview(sampleVideoUrl(config))
    }
  }, [config, imageSource, videoSource, imageFile, videoFile])

  const selectWorkflowVariant = useCallback(
    (variant: string) => {
      setWorkflowVariant(variant)
      setTunables(defaultTunablesForVariant(config, variant))
    },
    [config],
  )

  const setTunable = useCallback((key: string, value: string | number | boolean) => {
    setTunables((prev) => ({ ...prev, [key]: value }))
  }, [])

  useEffect(() => {
    if (restoredRef.current) return
    restoredRef.current = true

    void (async () => {
      try {
        const hist = await api.getHistory(20)
        const job = pickRestoreJob(hist.jobs)
        if (!job) {
          applySampleDefaults()
          return
        }

        const img = jobImageName(job)
        const vid = jobVideoName(job)
        if (img) {
          setImageName(img)
          setImagePreview(buildViewUrl(img, 'input'))
          setImageSource('restored')
        }
        if (vid) {
          setVideoName(vid)
          setVideoPreview(buildViewUrl(vid, 'input'))
          setVideoSource('restored')
        }
        if (job.workflow_variant) {
          setWorkflowVariant(job.workflow_variant)
          setTunables(
            job.tunables && Object.keys(job.tunables).length
              ? job.tunables
              : defaultTunablesForVariant(config, job.workflow_variant),
          )
        }

        const completed = hist.jobs.find((j) => j.status === 'completed' && j.results?.length)
        if (completed?.results?.[0]) {
          setVideoUrl(normalizeMediaUrl(completed.results[0].url))
          setPreviewState('success')
          setPromptId(completed.prompt_id)
          setMessage(`已恢复上次生成：${completed.prompt_id}`)
        }
      } catch {
        applySampleDefaults()
      } finally {
        historyCheckedRef.current = true
      }
    })()
  }, [applySampleDefaults, config])

  const resetDefaults = useCallback(() => {
    setWidth(config.defaults.width)
    setHeight(config.defaults.height)
    setSeconds(config.defaults.seconds)
  }, [config])

  const setImage = useCallback(
    (file: File | null) => {
      setImageFile(file)
      if (file) {
        setImagePreview(URL.createObjectURL(file))
        setImageSource('upload')
      } else {
        const names = sampleNamesFromConfig(config)
        setImagePreview(sampleImageUrl(config))
        setImageName(names.image)
        setImageSource('sample')
      }
    },
    [config],
  )

  const setVideo = useCallback(
    (file: File | null) => {
      setVideoFile(file)
      if (file) {
        setVideoPreview(URL.createObjectURL(file))
        setVideoSource('upload')
      } else {
        const names = sampleNamesFromConfig(config)
        setVideoPreview(sampleVideoUrl(config))
        setVideoName(names.video)
        setVideoSource('sample')
      }
    },
    [config],
  )

  const flushDiagnosticLog = useCallback(
    async (pid: string | null, afterFlush?: () => void) => {
      if (pid) {
        try {
          const entries = takeDiagnosticLog()
          await api.postDiagnosticLog(pid, entries)
        } catch {
          // diagnostic logging must not break UX
        }
      }
      afterFlush?.()
    },
    [takeDiagnosticLog],
  )

  const stopGeneration = useCallback(async () => {
    abortRef.current = true
    try {
      await api.interrupt()
    } catch {
      // ignore
    }
    await flushDiagnosticLog(promptId, disconnect)
    setPreviewState('idle')
    setMessage('已停止生成')
  }, [disconnect, flushDiagnosticLog, promptId])

  const pollResult = useCallback(
    async (pid: string, startMs: number, clipSeconds: number) => {
      const timeoutMs = pollTimeoutMs(clipSeconds)
      let delayMs = 5_000
      let finished = false
    loop:
      while (!abortRef.current && Date.now() - startMs < timeoutMs) {
        await new Promise((r) => setTimeout(r, delayMs))
        if (abortRef.current) break
        delayMs = 3000
        try {
          const res = await api.getResult(pid)
          if (applyResult(res, startMs, setPreviewState, setMessage, setVideoUrl, setFinalElapsed)) {
            finished = true
            break loop
          }
        } catch (err) {
          setPreviewState('error')
          setMessage(`❌ ${err instanceof Error ? err.message : String(err)}`)
          finished = true
          break loop
        }
      }
      if (!finished && !abortRef.current) {
        try {
          const res = await api.getResult(pid)
          if (applyResult(res, startMs, setPreviewState, setMessage, setVideoUrl, setFinalElapsed)) {
            await flushDiagnosticLog(pid, disconnect)
            return
          }
        } catch {
          // fall through to timeout message
        }
        setPreviewState('error')
        setMessage(
          `❌ 轮询超时（已等待 ${Math.floor((Date.now() - startMs) / 60000)} 分钟）。任务可能仍在后台运行，请点击「历史记录」查看。`,
        )
      }
      await flushDiagnosticLog(pid, disconnect)
    },
    [disconnect, flushDiagnosticLog],
  )

  const generate = useCallback(async () => {
    if (!warmupReady) {
      setPreviewState('idle')
      setMessage('模型预热中，请稍候……')
      return
    }
    abortRef.current = false
    reset()
    setMessage('')
    setVideoUrl(null)
    setPreviewState('generating')
    startElapsed()
    const startMs = Date.now()
    const clientId = randomClientId()
    let activePromptId: string | null = null

    try {
      let img = imageName
      let vid = videoName
      if (imageFile) {
        const up = await api.uploadFile(imageFile)
        img = up.name
        setImageName(img)
      }
      if (videoFile) {
        const up = await api.uploadFile(videoFile)
        vid = up.name
        setVideoName(vid)
      }

      const validated = await api.validateInput(img, vid)
      img = validated.image
      vid = validated.video

      const frames = Math.round(config.fps * seconds)
      const safeWidth = normalizeDimension(width, config.defaults.width || SAFE_WIDTH)
      const safeHeight = normalizeDimension(height, config.defaults.height || SAFE_HEIGHT)
      const forceSafeSize = safeWidth !== SAFE_WIDTH || safeHeight !== SAFE_HEIGHT
      const submitWidth = forceSafeSize ? SAFE_WIDTH : safeWidth
      const submitHeight = forceSafeSize ? SAFE_HEIGHT : safeHeight
      if (forceSafeSize) {
        setWidth(SAFE_WIDTH)
        setHeight(SAFE_HEIGHT)
        setMessage('检测节点当前仅稳定支持 468 x 832，已自动恢复为默认尺寸后提交。')
      }

      const { wsReady } = await prepareConnection(clientId)

      const gen = await api.generate({
        client_id: clientId,
        workflow_variant: workflowVariant,
        tunables,
        input_values: {
          '57:image': img,
          '997:video': vid,
          '1001:value': submitWidth,
          '1002:value': submitHeight,
          '1003:value': frames,
        },
      })
      activePromptId = gen.prompt_id
      setPromptId(gen.prompt_id)
      bindPrompt(gen.prompt_id, gen.prompt_snapshot)
      const channelHint = wsReady ? '' : '（进度通道降级为 HTTP 轮询）'
      setMessage(`任务已提交：${gen.prompt_id}（图像 ${img} · 视频 ${vid}）${channelHint}`)
      await pollResult(gen.prompt_id, startMs, seconds)
    } catch (err) {
      setPreviewState('error')
      setMessage(`❌ ${err instanceof Error ? err.message : String(err)}`)
      await flushDiagnosticLog(activePromptId, disconnect)
    }
  }, [
    bindPrompt,
    config.fps,
    config.defaults.height,
    config.defaults.width,
    disconnect,
    flushDiagnosticLog,
    imageFile,
    imageName,
    pollResult,
    prepareConnection,
    reset,
    seconds,
    startElapsed,
    videoFile,
    videoName,
    width,
    height,
    workflowVariant,
    tunables,
    warmupReady,
  ])

  const loadLatestFromHistory = useCallback(async () => {
    try {
      if (promptId) {
        const res = await api.getResult(promptId)
        if (!res.pending && res.results?.length) {
          setVideoUrl(normalizeMediaUrl(res.results[0].url))
          setPreviewState('success')
          setMessage(`已加载结果：${promptId}`)
          return
        }
      }
      const hist = await api.getHistory(20)
      const done = hist.jobs.find((j) => j.status === 'completed' && j.results?.length)
      if (!done) {
        setMessage('暂无已完成的历史记录')
        return
      }
      const item = done.results[0] as WorkflowResultItem
      setVideoUrl(normalizeMediaUrl(item.url))
      setPreviewState('success')
      setMessage(`已加载历史：${done.prompt_id}`)
    } catch (err) {
      setMessage(`❌ ${err instanceof Error ? err.message : String(err)}`)
    }
  }, [promptId])

  const submitImageName = imageFile?.name ?? imageName
  const submitVideoName = videoFile?.name ?? videoName

  return {
    width,
    height,
    seconds,
    setWidth,
    setHeight,
    setSeconds,
    resetDefaults,
    imageFile,
    videoFile,
    imagePreview,
    videoPreview,
    imageSource,
    videoSource,
    submitImageName,
    submitVideoName,
    workflowVariant,
    tunables,
    selectWorkflowVariant,
    setTunable,
    setImage,
    setVideo,
    previewState,
    message,
    videoUrl,
    finalElapsed,
    promptId,
    progress,
    generate,
    stopGeneration,
    loadLatestFromHistory,
    canGenerate: Boolean(imagePreview && videoPreview),
  }
}
