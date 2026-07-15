import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { WorkflowNode } from '../types/api'
import type { ProgressState } from '../types/workflow'
import { endpoints } from '../api/endpoints'
import { raceWithDeadline, sleepMs } from '../utils/deadline'

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
const MAX_RECONNECT_ATTEMPTS = 8
const HTTP_PROGRESS_INTERVAL_MS = 2500
const HTTP_PROGRESS_STALE_MS = 3000

export interface DiagnosticEntry extends Record<string, unknown> {
  ts: string
  event: string
  detail?: Record<string, unknown>
}

export type PrepareConnectionResult = { wsReady: boolean }

export function useComfyProgress() {
  const [progress, setProgress] = useState<ProgressState>(INITIAL)
  const wsRef = useRef<WebSocket | null>(null)
  const executedRef = useRef<Set<string>>(new Set())
  const snapshotRef = useRef<Record<string, WorkflowNode>>({})
  const promptIdRef = useRef<string>('')
  const clientIdRef = useRef<string>('')
  const elapsedRafRef = useRef<number | null>(null)
  const startTimeRef = useRef<number>(0)
  const diagnosticRef = useRef<DiagnosticEntry[]>([])
  const progressRef = useRef<ProgressState>(INITIAL)
  const reconnectAttemptRef = useRef(0)
  const allowReconnectRef = useRef(false)
  const lastProgressAtRef = useRef<number>(0)
  const stallDeadlineRef = useRef<number | null>(null)
  const stallRafRef = useRef<number | null>(null)
  const httpPollAbortRef = useRef(false)
  const httpPollActiveRef = useRef(false)
  const wsReadyRef = useRef(false)
  const attachHandlersRef = useRef<(ws: WebSocket) => void>(() => {})

  const logDiagnostic = useCallback((event: string, detail?: Record<string, unknown>) => {
    diagnosticRef.current.push({
      ts: new Date().toISOString(),
      event,
      detail,
    })
  }, [])

  const stopElapsed = useCallback(() => {
    if (elapsedRafRef.current !== null) {
      cancelAnimationFrame(elapsedRafRef.current)
      elapsedRafRef.current = null
    }
  }, [])

  const stopStallHint = useCallback(() => {
    stallDeadlineRef.current = null
    if (stallRafRef.current !== null) {
      cancelAnimationFrame(stallRafRef.current)
      stallRafRef.current = null
    }
  }, [])

  const stopHttpPoll = useCallback(() => {
    httpPollAbortRef.current = true
    httpPollActiveRef.current = false
  }, [])

  const startElapsed = useCallback(() => {
    stopElapsed()
    startTimeRef.current = Date.now()
    const tick = () => {
      const secs = Math.floor((Date.now() - startTimeRef.current) / 1000)
      setProgress((p) => {
        if (p.elapsedSeconds === secs) {
          progressRef.current = p
          return p
        }
        const next = { ...p, elapsedSeconds: secs }
        progressRef.current = next
        return next
      })
      elapsedRafRef.current = requestAnimationFrame(tick)
    }
    elapsedRafRef.current = requestAnimationFrame(tick)
  }, [stopElapsed])

  const reset = useCallback(() => {
    stopElapsed()
    stopStallHint()
    executedRef.current = new Set()
    reconnectAttemptRef.current = 0
    allowReconnectRef.current = false
    lastProgressAtRef.current = 0
    wsReadyRef.current = false
    diagnosticRef.current = []
    progressRef.current = INITIAL
    setProgress(INITIAL)
  }, [stopElapsed, stopStallHint])

  const disconnect = useCallback(() => {
    allowReconnectRef.current = false
    stopElapsed()
    stopStallHint()
    stopHttpPoll()
    wsRef.current?.close()
    wsRef.current = null
    wsReadyRef.current = false
  }, [stopElapsed, stopHttpPoll, stopStallHint])

  const updateOverall = useCallback((executedCount: number, nodePct: number, totalNodes: number) => {
    if (totalNodes <= 0) return 0
    const currentFraction = nodePct > 0 ? Math.min(1, nodePct / 100) : 0
    const completed = Math.max(0, executedCount - 1)
    return Math.min(100, ((completed + currentFraction) / totalNodes) * 100)
  }, [])

  const applyHttpProgress = useCallback(
    (snap: {
      workflow_progress: number
      node_progress: number
      current_node_name: string
      executed_nodes: number
      total_nodes: number
      status?: string
    }) => {
      lastProgressAtRef.current = Date.now()
      setProgress((p) => {
        const next = {
          ...p,
          workflowProgress: snap.workflow_progress,
          nodeProgress: snap.node_progress,
          currentNodeName: snap.current_node_name || p.currentNodeName,
          executedNodes: snap.executed_nodes || p.executedNodes,
          totalNodes: snap.total_nodes || p.totalNodes,
          progressHint: p.progressHint,
        }
        progressRef.current = next
        return next
      })
    },
    [],
  )

  const startHttpProgressPoll = useCallback(() => {
    if (httpPollActiveRef.current) return
    const pid = promptIdRef.current
    if (!pid) return
    httpPollAbortRef.current = false
    httpPollActiveRef.current = true

    void (async () => {
      while (!httpPollAbortRef.current && promptIdRef.current === pid) {
        const stale =
          !wsReadyRef.current ||
          lastProgressAtRef.current === 0 ||
          Date.now() - lastProgressAtRef.current > HTTP_PROGRESS_STALE_MS
        if (stale) {
          try {
            const snap = await api.getWorkflowProgress(pid)
            if (httpPollAbortRef.current || promptIdRef.current !== pid) break
            if (snap.found) {
              applyHttpProgress(snap)
              logDiagnostic('http_progress', {
                promptId: pid,
                workflow: snap.workflow_progress,
                node: snap.node_progress,
              })
            }
          } catch {
            // ignore transient poll errors
          }
        }
        await sleepMs(HTTP_PROGRESS_INTERVAL_MS)
      }
      httpPollActiveRef.current = false
    })()
  }, [applyHttpProgress, logDiagnostic])

  const schedulePoseHint = useCallback(() => {
    stopStallHint()
    stallDeadlineRef.current = Date.now() + POSE_STALL_HINT_MS
    const tick = () => {
      const deadline = stallDeadlineRef.current
      if (deadline === null) return
      if (Date.now() >= deadline) {
        setProgress((p) => {
          const isPose =
            p.currentNodeName.includes('Pose') ||
            p.currentNodeName.includes('姿态') ||
            p.currentNodeName.includes('508')
          if (!isPose || p.nodeProgress > 0) return p
          const next = {
            ...p,
            progressHint: '姿态检测初始化中，首帧 ONNX 加载较慢，请稍候…',
          }
          progressRef.current = next
          return next
        })
        stallDeadlineRef.current = null
        return
      }
      stallRafRef.current = requestAnimationFrame(tick)
    }
    stallRafRef.current = requestAnimationFrame(tick)
  }, [stopStallHint])

  const tryReconnect = useCallback(async () => {
    if (!allowReconnectRef.current || !clientIdRef.current) return
    if (reconnectAttemptRef.current >= MAX_RECONNECT_ATTEMPTS) {
      logDiagnostic('ws_reconnect_exhausted', {
        attempts: reconnectAttemptRef.current,
        clientId: clientIdRef.current,
      })
      wsReadyRef.current = false
      startHttpProgressPoll()
      return
    }
    const attempt = reconnectAttemptRef.current + 1
    reconnectAttemptRef.current = attempt
    const backoffMs = Math.min(8000, 400 * 2 ** (attempt - 1))
    logDiagnostic('ws_reconnect_attempt', {
      clientId: clientIdRef.current,
      attempt,
      backoffMs,
    })
    await sleepMs(backoffMs)
    if (!allowReconnectRef.current || !clientIdRef.current) return
    try {
      const retry = new WebSocket(endpoints.wsProxy(clientIdRef.current))
      wsRef.current = retry
      attachHandlersRef.current(retry)
    } catch {
      wsReadyRef.current = false
      startHttpProgressPoll()
    }
  }, [logDiagnostic, startHttpProgressPoll])

  const attachHandlers = useCallback(
    (ws: WebSocket) => {
      ws.onopen = () => {
        wsReadyRef.current = true
        reconnectAttemptRef.current = 0
        logDiagnostic('ws_open', { clientId: clientIdRef.current })
      }

      ws.onerror = () => {
        logDiagnostic('ws_error', { clientId: clientIdRef.current })
      }

      ws.onclose = () => {
        wsReadyRef.current = false
        logDiagnostic('ws_close', {
          clientId: clientIdRef.current,
          reconnectAttempt: reconnectAttemptRef.current,
        })
        if (allowReconnectRef.current && clientIdRef.current) {
          void tryReconnect()
        }
      }

      ws.onmessage = (event) => {
        if (typeof event.data !== 'string') return
        try {
          const msg = JSON.parse(event.data) as { type: string; data: Record<string, unknown> }
          logDiagnostic('ws_message', { type: msg.type, data: msg.data })

          const totalNodes = Object.keys(snapshotRef.current).length || progressRef.current.totalNodes

          if (msg.type === 'execution_start') {
            executedRef.current = new Set()
          }
          if (msg.type === 'progress') {
            lastProgressAtRef.current = Date.now()
            const value = Number(msg.data.value ?? 0)
            const max = Number(msg.data.max ?? 1)
            const nodeProgress = max > 0 ? Math.min(100, (value / max) * 100) : 0
            setProgress((p) => {
              const next = {
                ...p,
                nodeProgress,
                progressHint: '',
                workflowProgress: updateOverall(executedRef.current.size, nodeProgress, totalNodes),
              }
              progressRef.current = next
              return next
            })
          }
          if (msg.type === 'progress_state') {
            const pid = msg.data.prompt_id as string | undefined
            if (pid && promptIdRef.current && pid !== promptIdRef.current) return
            const nodes = msg.data.nodes as
              | Record<string, { value: number; max: number; state: string }>
              | undefined
            if (!nodes) return

            for (const [nodeId, nodeState] of Object.entries(nodes)) {
              if (nodeState.state === 'finished') {
                executedRef.current.add(nodeId)
              }
            }

            const running = Object.entries(nodes).find(([, nodeState]) => nodeState.state === 'running')
            if (!running) return

            const [nodeId, nodeState] = running
            lastProgressAtRef.current = Date.now()
            executedRef.current.add(nodeId)
            const max = Number(nodeState.max ?? 1)
            const value = Number(nodeState.value ?? 0)
            const nodeProgress = max > 0 ? Math.min(100, (value / max) * 100) : 0
            const nodeDef = snapshotRef.current[nodeId]
            const title = nodeDef?._meta?.title || nodeDef?.class_type || nodeId
            const resolvedTotal = totalNodes || Object.keys(snapshotRef.current).length
            setProgress((p) => {
              const next = {
                ...p,
                currentNodeName: `${nodeId} · ${title}`,
                executedNodes: executedRef.current.size,
                totalNodes: resolvedTotal || p.totalNodes,
                nodeProgress,
                progressHint: '',
                workflowProgress: updateOverall(
                  executedRef.current.size,
                  nodeProgress,
                  resolvedTotal || p.totalNodes,
                ),
              }
              progressRef.current = next
              return next
            })
            schedulePoseHint()
          }
          if (msg.type === 'executing') {
            const node = msg.data.node as string | null
            const pid = msg.data.prompt_id as string
            if (pid && promptIdRef.current && pid !== promptIdRef.current) return
            if (node) {
              executedRef.current.add(node)
              const nodeDef = snapshotRef.current[node]
              const title = nodeDef?._meta?.title || nodeDef?.class_type || node
              setProgress((p) => {
                const next = {
                  ...p,
                  currentNodeName: `${node} · ${title}`,
                  executedNodes: executedRef.current.size,
                  totalNodes: totalNodes || p.totalNodes,
                  workflowProgress: updateOverall(
                    executedRef.current.size,
                    p.nodeProgress,
                    totalNodes || p.totalNodes,
                  ),
                  nodeProgress: 0,
                  progressHint: '',
                }
                progressRef.current = next
                return next
              })
              schedulePoseHint()
            } else if (!promptIdRef.current || pid === promptIdRef.current) {
              setProgress((p) => {
                const next = { ...p, workflowProgress: 100, nodeProgress: 100, progressHint: '' }
                progressRef.current = next
                return next
              })
            }
          }
        } catch {
          // ignore malformed
        }
      }
    },
    [logDiagnostic, schedulePoseHint, tryReconnect, updateOverall],
  )

  attachHandlersRef.current = attachHandlers

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
    async (clientId: string): Promise<PrepareConnectionResult> => {
      allowReconnectRef.current = false
      stopStallHint()
      stopHttpPoll()
      wsRef.current?.close()
      wsRef.current = null
      wsReadyRef.current = false

      executedRef.current = new Set()
      reconnectAttemptRef.current = 0
      lastProgressAtRef.current = 0
      allowReconnectRef.current = true
      if (elapsedRafRef.current === null) {
        startElapsed()
      }
      logDiagnostic('ws_prepare', { clientId })

      const ws = openSocket(clientId)
      const openPromise = new Promise<boolean>((resolve) => {
        if (ws.readyState === WebSocket.OPEN) {
          resolve(true)
          return
        }
        const onOpen = () => {
          cleanup()
          resolve(true)
        }
        const onError = () => {
          cleanup()
          resolve(false)
        }
        const cleanup = () => {
          ws.removeEventListener('open', onOpen)
          ws.removeEventListener('error', onError)
        }
        ws.addEventListener('open', onOpen)
        ws.addEventListener('error', onError)
      })

      const raced = await raceWithDeadline(openPromise, WS_OPEN_TIMEOUT_MS)
      if (raced.ok && raced.value) {
        wsReadyRef.current = true
        logDiagnostic('ws_open', { clientId, via: 'prepare' })
        return { wsReady: true }
      }
      wsReadyRef.current = false
      logDiagnostic('ws_open_soft_fail', {
        clientId,
        reason: raced.ok ? 'error' : 'timeout',
      })
      return { wsReady: false }
    },
    [logDiagnostic, openSocket, startElapsed, stopHttpPoll, stopStallHint],
  )

  const connect = useCallback(
    (clientId: string, promptSnapshot: Record<string, WorkflowNode>, promptId: string) => {
      snapshotRef.current = promptSnapshot
      promptIdRef.current = promptId
      clientIdRef.current = clientId
      setProgress((p) => {
        const next = { ...p, totalNodes: Object.keys(promptSnapshot).length }
        progressRef.current = next
        return next
      })
      if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
        allowReconnectRef.current = true
        openSocket(clientId)
      }
    },
    [openSocket],
  )

  const bindPrompt = useCallback(
    (promptId: string, snapshot: Record<string, WorkflowNode>) => {
      promptIdRef.current = promptId
      snapshotRef.current = snapshot
      logDiagnostic('bind_prompt', { promptId, nodeCount: Object.keys(snapshot).length })
      setProgress((p) => {
        const next = { ...p, totalNodes: Object.keys(snapshot).length }
        progressRef.current = next
        return next
      })
      startHttpProgressPoll()
    },
    [logDiagnostic, startHttpProgressPoll],
  )

  const takeDiagnosticLog = useCallback((): DiagnosticEntry[] => {
    const copy = [...diagnosticRef.current]
    const lastProgress = { ...progressRef.current }
    copy.push({
      ts: new Date().toISOString(),
      event: 'progress_snapshot',
      detail: lastProgress as unknown as Record<string, unknown>,
    })
    return copy
  }, [])

  useEffect(() => () => disconnect(), [disconnect])

  return {
    progress,
    prepareConnection,
    connect,
    disconnect,
    reset,
    bindPrompt,
    takeDiagnosticLog,
    startElapsed,
  }
}
