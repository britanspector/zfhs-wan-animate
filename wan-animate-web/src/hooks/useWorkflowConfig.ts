import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { buildViewUrl } from '../api/endpoints'
import type { WorkflowConfig } from '../types/workflow'
import { defaultTunablesForVariant } from '../types/workflow'

const FALLBACK: WorkflowConfig = {
  workflow_id: 'P07-animate-v4',
  default_workflow_variant: 'v4',
  variants: [
    {
      variant: 'v4',
      id: 'P07-animate-v4',
      label: '标准动作迁移',
      description: '更贴近参考视频整体观感与表情',
      file: 'workflows/p07_animate_v4.json',
      default_tunables: {},
    },
    {
      variant: 'v5',
      id: 'P07-animate-v5',
      label: '保身份动作迁移',
      description: '尽量保留参考图人物外形，主要迁移动作姿态',
      file: 'workflows/p07_animate_v5.json',
      default_tunables: {},
    },
  ],
  tunables: [],
  save_node_id: '867',
  fps: 30,
  defaults: { width: 468, height: 832, seconds: 30 },
  duration_options: [
    { label: '10 秒内', seconds: 10, frames: 300 },
    { label: '20 秒内', seconds: 20, frames: 600 },
    { label: '30 秒内', seconds: 30, frames: 900 },
  ],
  samples: {
    image_preview_url: buildViewUrl('image (17).png', 'input'),
  },
}

export function useWorkflowConfig() {
  const [config, setConfig] = useState<WorkflowConfig>(FALLBACK)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .getWorkflowConfig()
      .then((c) => {
        const videoName = c.samples.video?.split('/').pop() ?? '5053929f1d2c2ef117a3a8b8c02075c7da53e5380365bc2f8a87992986058e39.mp4'
        const merged: WorkflowConfig = {
          ...FALLBACK,
          ...c,
          variants: c.variants?.length ? c.variants : FALLBACK.variants,
          tunables: c.tunables?.length ? c.tunables : FALLBACK.tunables,
          samples: {
            ...c.samples,
            image_preview_url: c.samples.image_preview_url ?? buildViewUrl('image (17).png', 'input'),
            video_preview_url: buildViewUrl(videoName, 'input'),
          },
        }
        for (const v of merged.variants) {
          if (!Object.keys(v.default_tunables).length) {
            v.default_tunables = defaultTunablesForVariant(merged, v.variant)
          }
        }
        setConfig(merged)
      })
      .catch(() => setConfig(FALLBACK))
      .finally(() => setLoading(false))
  }, [])

  return { config, loading }
}
