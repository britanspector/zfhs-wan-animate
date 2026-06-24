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
}

export function useComfyProgress() {
  const [progress, setProgress] = useState<ProgressState>(INITIAL)
  const wsRef = useRef<WebSocket | null>(null)
  const executedRef = useRef<Set<string>>(new Set())
  const snapshotRef = useRef<Record<string, WorkflowNode>>({})
  const promptIdRef = useRef<string>('')
  const timerRef = useRef<number | null>(null)
  const startTimeRef = useRef<number>(0)

  const stopTimer = () => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  const reset = useCallback(() => {
    executedRef.current = new Set()
    setProgress(INITIAL)
  }, [])

  const disconnect = useCallback(() => {
    stopTimer()
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  const connect = useCallback(
    (clientId: string, promptSnapshot: Record<string, WorkflowNode>, promptId: string) => {
      disconnect()
      reset()
      snapshotRef.current = promptSnapshot
      promptIdRef.current = promptId
      const totalNodes = Object.keys(promptSnapshot).length
      startTimeRef.current = Date.now()
      timerRef.current = window.setInterval(() => {
        setProgress((p) => ({
          ...p,
          elapsedSeconds: Math.floor((Date.now() - startTimeRef.current) / 1000),
        }))
      }, 1000)

      const ws = new WebSocket(endpoints.wsProxy(clientId))
      wsRef.current = ws

      const updateOverall = (executedCount: number, nodePct: number) => {
        if (totalNodes <= 0) return 0
        const currentFraction = nodePct > 0 ? Math.min(1, nodePct / 100) : 0
        const completed = Math.max(0, executedCount - 1)
        return Math.min(100, ((completed + currentFraction) / totalNodes) * 100)
      }

      ws.onmessage = (event) => {
        if (typeof event.data !== 'string') return
        try {
          const msg = JSON.parse(event.data) as { type: string; data: Record<string, unknown> }
          if (msg.type === 'execution_start') {
            executedRef.current = new Set()
          }
          if (msg.type === 'progress') {
            const value = Number(msg.data.value ?? 0)
            const max = Number(msg.data.max ?? 1)
            const nodeProgress = max > 0 ? Math.min(100, (value / max) * 100) : 0
            setProgress((p) => ({
              ...p,
              nodeProgress,
              workflowProgress: updateOverall(executedRef.current.size, nodeProgress),
            }))
          }
          if (msg.type === 'executing') {
            const node = msg.data.node as string | null
            const pid = msg.data.prompt_id as string
            if (pid && pid !== promptIdRef.current) return
            if (node) {
              executedRef.current.add(node)
              const nodeDef = snapshotRef.current[node]
              const title = nodeDef?._meta?.title || nodeDef?.class_type || node
              setProgress((p) => ({
                ...p,
                currentNodeName: `${node} · ${title}`,
                executedNodes: executedRef.current.size,
                totalNodes,
                workflowProgress: updateOverall(executedRef.current.size, p.nodeProgress),
                nodeProgress: 0,
              }))
            } else if (pid === promptIdRef.current) {
              setProgress((p) => ({ ...p, workflowProgress: 100, nodeProgress: 100 }))
            }
          }
        } catch {
          // ignore malformed
        }
      }
    },
    [disconnect, reset],
  )

  const bindPrompt = useCallback((promptId: string, snapshot: Record<string, WorkflowNode>) => {
    promptIdRef.current = promptId
    snapshotRef.current = snapshot
    setProgress((p) => ({
      ...p,
      totalNodes: Object.keys(snapshot).length,
    }))
  }, [])

  useEffect(() => () => disconnect(), [disconnect])

  return { progress, connect, disconnect, reset, bindPrompt }
}
