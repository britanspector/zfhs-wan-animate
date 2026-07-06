export interface GpuInfo {
  hasGPU: boolean
  gpuName: string
  isRTX5090: boolean
}

export interface ComfyStatus {
  running: boolean
  starting: boolean
  reason: string
  version?: string
}

export interface WarmupStatus {
  ready: boolean
  warming: boolean
  skipped: boolean
  milestone: string | null
  comfy_pid: number | null
  warmup_running: boolean
}

export interface UploadResponse {
  name: string
  subfolder: string
  type: string
  fallback?: string
}

export interface WorkflowResultItem {
  type: string
  filename: string
  subfolder: string
  url: string
  view_url: string
}

export interface WorkflowResult {
  success: boolean
  pending: boolean
  prompt_id: string
  results: WorkflowResultItem[]
  error?: string
}

export interface GenerateResponse {
  success: boolean
  prompt_id: string
  client_id: string
  number: number
  prompt_snapshot: Record<string, WorkflowNode>
}

export interface WorkflowNode {
  class_type: string
  inputs: Record<string, unknown>
  _meta?: { title?: string }
}

export interface JobRecord {
  id: string
  prompt_id: string
  workflow_id: string
  status: string
  results: WorkflowResultItem[]
  image?: string
  video?: string
  workflow_variant?: string
  tunables?: Record<string, string | number | boolean>
  input_values?: Record<string, string | number>
  width?: number
  height?: number
  seconds?: number
  created_at: string
}

export interface HistoryResponse {
  success: boolean
  jobs: JobRecord[]
}
