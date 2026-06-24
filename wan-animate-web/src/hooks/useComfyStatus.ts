import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { ComfyStatus } from '../types/api'

export function useComfyStatus(pollMs = 5000) {
  const [status, setStatus] = useState<ComfyStatus | null>(null)
  const [starting, setStarting] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const s = await api.getComfyStatus()
      setStatus(s)
      return s
    } catch {
      setStatus({ running: false, starting: false, reason: 'unreachable' })
      return null
    }
  }, [])

  const startComfy = useCallback(async () => {
    setStarting(true)
    try {
      await api.startComfy()
      const deadline = Date.now() + 120_000
      while (Date.now() < deadline) {
        const s = await refresh()
        if (s?.running) return true
        await new Promise((r) => setTimeout(r, 2000))
      }
      return false
    } finally {
      setStarting(false)
    }
  }, [refresh])

  useEffect(() => {
    refresh()
    const id = window.setInterval(refresh, pollMs)
    return () => window.clearInterval(id)
  }, [pollMs, refresh])

  return {
    status,
    isRunning: status?.running ?? false,
    starting,
    refresh,
    startComfy,
  }
}
