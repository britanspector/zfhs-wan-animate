import { useCallback, useEffect, useRef, useState } from 'react'
import type { WorkflowNode } from '../types/api'
import type { ProgressState } from '../types/workflow'
import { endpoints } from '../api/endpoints'

const INITIAL: ProgressState = {
  workflowProgress: 0,
  nodeProgress: 0,
  currentNodeName: '',
  executedNodes: 0,
  totalNodes: 0,
  elapsedSeconds: 0,
  progressHint: '',
}

const WS_OPEN_TIMEOUT_MS = 5000
const POSE_STALL_HINT_MS = 15_000

export interface DiagnosticEntry extends Record<string, unknown> {
  ts: string
  event: string
  detail?: Record<string, unknown>
}

export function useComfyProgress() {
  const [progress, setProgress] = useState<ProgressState>(INITIAL)
  const wsRef = useRef<WebSocket | null>(null)
  const executedRef = useRef<Set<string>>(new Set())
  const snapshotRef = useRef<Record<string, WorkflowNode>>({})
  const promptIdRef = useRef<string>('')
  const clientIdRef = useRef<string>('')
  const timerRef = useRef<number | null>(null)
  const startTimeRef = useRef<number>(0)
  const diagnosticRef = useRef<DiagnosticEntry[]>([])
  const reconnectUsedRef = useRef(false)
  const allowReconnectRef = useRef(false)
  const lastProgressAtRef = useRef<number>(0)
  const stallTimerRef = useRef<number | null>(null)

  const logDiagnostic = useCallback((event: string, detail?: Record<string, unknown>) => {
    diagnosticRef.current.push({
      ts: new Date().toISOString(),
      event,
      detail,
    })
  }, [])

  const stopTimer = () => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (stallTimerRef.current !== null) {
      window.clearTimeout(stallTimerRef.current)
      stallTimerRef.current = null
    }
  }

  const reset = useCallback(() => {
    executedRef.current = new Set()
    reconnectUsedRef.current = false
    allowReconnectRef.current = false
    lastProgressAtRef.current = 0
    diagnosticRef.current = []
    setProgress(INITIAL)
  }, [])

  const disconnect = useCallback(() => {
    allowReconnectRef.current = false
    stopTimer()
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  const updateOverall = useCallback((executedCount: number, nodePct: number, totalNodes: number) => {
    if (totalNodes <= 0) return 0
    const currentFraction = nodePct > 0 ? Math.min(1, nodePct / 100) : 0
    const completed = Math.max(0, executedCount - 1)
    return Math.min(100, ((completed + currentFraction) / totalNodes) * 100)
  }, [])

  const schedulePoseHint = useCallback(() => {
    if (stallTimerRef.current !== null) {
      window.clearTimeout(stallTimerRef.current)
    }
    stallTimerRef.current = window.setTimeout(() => {
      setProgress((p) => {
        const isPose =
          p.currentNodeName.includes('Pose') ||
          p.currentNodeName.includes('姿态') ||
          p.currentNodeName.includes('508')
        if (!isPose || p.nodeProgress > 0) return p
        return {
          ...p,
          progressHint: '姿态检测初始化中，首帧 ONNX 加载较慢，请稍候…',
        }
      })
    }, POSE_STALL_HINT_MS)
  }, [])

  const attachHandlers = useCallback(
    (ws: WebSocket) => {
      ws.onopen = () => {
        logDiagnostic('ws_open', { clientId: clientIdRef.current })
      }

      ws.onerror = () => {
        logDiagnostic('ws_error', { clientId: clientIdRef.current })
      }

      ws.onclose = () => {
        logDiagnostic('ws_close', {
          clientId: clientIdRef.current,
          reconnectUsed: reconnectUsedRef.current,
        })
        if (allowReconnectRef.current && !reconnectUsedRef.current && clientIdRef.current) {
          reconnectUsedRef.current = true
          logDiagnostic('ws_reconnect_attempt', { clientId: clientIdRef.current })
          const retry = new WebSocket(endpoints.wsProxy(clientIdRef.current))
          wsRef.current = retry
          attachHandlers(retry)
        }
      }

      ws.onmessage = (event) => {
        if (typeof event.data !== 'string') return
        try {
          const msg = JSON.parse(event.data) as { type: string; data: Record<string, unknown> }
          logDiagnostic('ws_message', { type: msg.type, data: msg.data })

          const totalNodes = Object.keys(snapshotRef.current).length || progress.totalNodes

          if (msg.type === 'execution_start') {
            executedRef.current = new Set()
          }
          if (msg.type === 'progress') {
            lastProgressAtRef.current = Date.now()
            const value = Number(msg.data.value ?? 0)
            const max = Number(msg.data.max ?? 1)
            const nodeProgress = max > 0 ? Math.min(100, (value / max) * 100) : 0
            setProgress((p) => ({
              ...p,
              nodeProgress,
              progressHint: '',
              workflowProgress: updateOverall(executedRef.current.size, nodeProgress, totalNodes),
            }))
          }
          if (msg.type === 'executing') {
            const node = msg.data.node as string | null
            const pid = msg.data.prompt_id as string
            if (pid && promptIdRef.current && pid !== promptIdRef.current) return
            if (node) {
              executedRef.current.add(node)
              const nodeDef = snapshotRef.current[node]
              const title = nodeDef?._meta?.title || nodeDef?.class_type || node
              setProgress((p) => ({
                ...p,
                currentNodeName: `${node} · ${title}`,
                executedNodes: executedRef.current.size,
                totalNodes: totalNodes || p.totalNodes,
                workflowProgress: updateOverall(executedRef.current.size, p.nodeProgress, totalNodes || p.totalNodes),
                nodeProgress: 0,
                progressHint: '',
              }))
              schedulePoseHint()
            } else if (!promptIdRef.current || pid === promptIdRef.current) {
              setProgress((p) => ({ ...p, workflowProgress: 100, nodeProgress: 100, progressHint: '' }))
            }
          }
        } catch {
          // ignore malformed
        }
      }
    },
    [logDiagnostic, progress.totalNodes, schedulePoseHint, updateOverall],
  )

  const openSocket = useCallback(
    (clientId: string) => {
      clientIdRef.current = clientId
      const ws = new WebSocket(endpoints.wsProxy(clientId))
      wsRef.current = ws
      attachHandlers(ws)
      return ws
    },
    [attachHandlers],
  )

  const prepareConnection = useCallback(
    (clientId: string): Promise<void> => {
      disconnect()
      reset()
      allowReconnectRef.current = true
      startTimeRef.current = Date.now()
      timerRef.current = window.setInterval(() => {
        setProgress((p) => ({
          ...p,
          elapsedSeconds: Math.floor((Date.now() - startTimeRef.current) / 1000),
        }))
      }, 1000)

      logDiagnostic('ws_prepare', { clientId })

      return new Promise((resolve, reject) => {
        const ws = openSocket(clientId)
        const timeout = window.setTimeout(() => {
          logDiagnostic('ws_open_timeout', { clientId })
          reject(new Error('WebSocket 连接超时，请确认 ComfyUI 已启动'))
        }, WS_OPEN_TIMEOUT_MS)

        const onOpen = () => {
          window.clearTimeout(timeout)
          ws.removeEventListener('open', onOpen)
          ws.removeEventListener('error', onError)
          resolve()
        }
        const onError = () => {
          window.clearTimeout(timeout)
          ws.removeEventListener('open', onOpen)
          ws.removeEventListener('error', onError)
          reject(new Error('WebSocket 连接失败'))
        }
        if (ws.readyState === WebSocket.OPEN) {
          window.clearTimeout(timeout)
          resolve()
        } else {
          ws.addEventListener('open', onOpen)
          ws.addEventListener('error', onError)
        }
      })
    },
    [disconnect, logDiagnostic, openSocket, reset],
  )

  const connect = useCallback(
    (clientId: string, promptSnapshot: Record<string, WorkflowNode>, promptId: string) => {
      snapshotRef.current = promptSnapshot
      promptIdRef.current = promptId
      clientIdRef.current = clientId
      setProgress((p) => ({
        ...p,
        totalNodes: Object.keys(promptSnapshot).length,
      }))
      if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
        allowReconnectRef.current = true
        openSocket(clientId)
      }
    },
    [openSocket],
  )

  const bindPrompt = useCallback((promptId: string, snapshot: Record<string, WorkflowNode>) => {
    promptIdRef.current = promptId
    snapshotRef.current = snapshot
    logDiagnostic('bind_prompt', { promptId, nodeCount: Object.keys(snapshot).length })
    setProgress((p) => ({
      ...p,
      totalNodes: Object.keys(snapshot).length,
    }))
  }, [logDiagnostic])

  const takeDiagnosticLog = useCallback((): DiagnosticEntry[] => {
    const copy = [...diagnosticRef.current]
    const lastProgress = { ...progress }
    copy.push({
      ts: new Date().toISOString(),
      event: 'progress_snapshot',
      detail: lastProgress as unknown as Record<string, unknown>,
    })
    return copy
  }, [progress])

  useEffect(() => () => disconnect(), [disconnect])

  return {
    progress,
    prepareConnection,
    connect,
    disconnect,
    reset,
    bindPrompt,
    takeDiagnosticLog,
  }
}
