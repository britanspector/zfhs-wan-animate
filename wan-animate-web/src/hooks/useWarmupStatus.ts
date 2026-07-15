import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { WarmupStatus } from '../types/api'

export function useWarmupStatus(isRunning: boolean) {
  const [status, setStatus] = useState<WarmupStatus | null>(null)

  const refresh = useCallback(async () => {
    if (!isRunning) {
      setStatus(null)
      return null
    }
    try {
      const s = await api.getWarmupStatus()
      setStatus(s)
      return s
    } catch {
      setStatus({
        ready: false,
        warming: true,
        skipped: false,
        milestone: null,
        comfy_pid: null,
        warmup_running: false,
      })
      return null
    }
  }, [isRunning])

  useEffect(() => {
    if (!isRunning) {
      setStatus(null)
      return
    }
    void refresh()
    const pollMs = status?.ready ? 30_000 : 3_000
    const id = window.setInterval(() => {
      void refresh()
    }, pollMs)
    return () => window.clearInterval(id)
  }, [isRunning, refresh, status?.ready])

  const warmupReady = !isRunning || (status?.ready ?? false)
  const warming = Boolean(isRunning && status && !status.ready && status.warming)

  return {
    status,
    warmupReady,
    warming,
    refresh,
  }
}
