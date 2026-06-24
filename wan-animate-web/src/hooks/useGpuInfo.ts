import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { GpuInfo } from '../types/api'

export function useGpuInfo() {
  const [gpu, setGpu] = useState<GpuInfo | null>(null)

  useEffect(() => {
    api.getGpuInfo().then(setGpu).catch(() => setGpu({ hasGPU: false, gpuName: '', isRTX5090: false }))
  }, [])

  return gpu
}
