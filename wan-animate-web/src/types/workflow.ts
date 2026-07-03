export const WORKFLOW_ID = 'P07-animate-v4'

export type TunableGroup = 'identity' | 'sampler' | 'lora' | 'prompt' | 'other'

export interface DurationOption {
  label: string
  seconds: number
  frames: number
}

export interface WorkflowVariantConfig {
  variant: string
  id: string
  label: string
  description: string
  file: string
  default_tunables: Record<string, string | number | boolean>
}

export interface TunableField {
  key: string
  label: string
  type: 'float' | 'bool' | 'select' | 'int' | 'text' | 'lora_switch'
  min?: number
  max?: number
  step?: number
  options?: string[]
  group?: TunableGroup
  rows?: number
  hint?: string
}

export interface WorkflowConfig {
  workflow_id: string
  default_workflow_variant: string
  variants: WorkflowVariantConfig[]
  tunables: TunableField[]
  save_node_id: string
  fps: number
  defaults: { width: number; height: number; seconds: number }
  duration_options: DurationOption[]
  samples: {
    image?: string
    video?: string
    image_preview_url?: string
    video_preview_url?: string
  }
}

export type PreviewState = 'idle' | 'generating' | 'loadingResult' | 'success' | 'error'

export interface ProgressState {
  workflowProgress: number
  nodeProgress: number
  currentNodeName: string
  executedNodes: number
  totalNodes: number
  elapsedSeconds: number
  progressHint?: string
}

export const TUNABLE_GROUP_LABELS: Record<TunableGroup, string> = {
  identity: '身份与姿态',
  sampler: '采样',
  lora: 'LoRA',
  prompt: '提示词',
  other: '其他',
}

export const TUNABLE_GROUP_ORDER: TunableGroup[] = ['identity', 'sampler', 'lora', 'prompt', 'other']

export function defaultTunablesForVariant(
  config: WorkflowConfig,
  variant: string,
): Record<string, string | number | boolean> {
  const found = config.variants.find((v) => v.variant === variant)
  const raw = { ...(found?.default_tunables ?? {}) }
  const out: Record<string, string | number | boolean> = {}
  for (const field of config.tunables) {
    if (field.key in raw) {
      out[field.key] = coerceTunableValue(field, raw[field.key])
    }
  }
  for (const [key, value] of Object.entries(raw)) {
    if (!(key in out)) out[key] = value
  }
  return out
}

export function coerceTunableValue(
  field: TunableField,
  value: string | number | boolean,
): string | number | boolean {
  if (field.type === 'bool') {
    if (typeof value === 'boolean') return value
    if (typeof value === 'string') return value.toLowerCase() === 'true'
    return Boolean(value)
  }
  if (field.type === 'int') return Math.round(Number(value))
  if (field.type === 'float' || field.type === 'lora_switch') return Number(value)
  if (field.type === 'text') return String(value ?? '')
  return value
}

export function groupTunableFields(schema: TunableField[]): Map<TunableGroup, TunableField[]> {
  const map = new Map<TunableGroup, TunableField[]>()
  for (const field of schema) {
    const group = field.group ?? 'other'
    const list = map.get(group) ?? []
    list.push(field)
    map.set(group, list)
  }
  return map
}
