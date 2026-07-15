import type {
  ComfyStatus,
  GenerateResponse,
  GpuInfo,
  HistoryResponse,
  UploadResponse,
  WarmupStatus,
  WorkflowProgressResponse,
  WorkflowResult,
} from '../types/api'
import { WORKFLOW_ID } from '../types/workflow'
import type { WorkflowConfig } from '../types/workflow'
import { endpoints } from './endpoints'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  getGpuInfo: () => request<GpuInfo>(endpoints.gpuInfo),
  getComfyStatus: () => request<ComfyStatus>(endpoints.comfyStatus),
  getWarmupStatus: () => request<WarmupStatus>(endpoints.warmupStatus),
  startComfy: () => request<ComfyStatus & { success?: boolean }>(endpoints.comfyStart, { method: 'POST' }),
  stopComfy: () => request<{ success: boolean }>(endpoints.comfyStop, { method: 'POST' }),
  interrupt: () => request<{ success: boolean }>(endpoints.comfyInterrupt, { method: 'POST' }),
  getWorkflowConfig: () => request<WorkflowConfig>(endpoints.workflowConfig(WORKFLOW_ID)),
  uploadFile: async (file: File): Promise<UploadResponse> => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('overwrite', 'true')
    return request<UploadResponse>(endpoints.comfyUpload, { method: 'POST', body: fd })
  },
  generate: (body: {
    input_values: Record<string, string | number | boolean>
    client_id: string
    workflow_variant?: string
    tunables?: Record<string, string | number | boolean>
  }) =>
    request<GenerateResponse>(endpoints.workflowGenerate, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workflow_id: WORKFLOW_ID, ...body }),
    }),
  validateInput: (image: string, video: string) =>
    request<{ ok: boolean; image: string; video: string }>(endpoints.workflowValidateInput, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image, video }),
    }),
  postDiagnosticLog: (promptId: string, entries: Array<Record<string, unknown>>) =>
    request<{ success: boolean }>(endpoints.workflowDiagnosticLog, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt_id: promptId, entries }),
    }),
  getResult: (promptId: string) =>
    request<WorkflowResult>(`${endpoints.workflowResult}?prompt_id=${encodeURIComponent(promptId)}`),
  getWorkflowProgress: (promptId: string) =>
    request<WorkflowProgressResponse>(
      `${endpoints.workflowProgress}?prompt_id=${encodeURIComponent(promptId)}`,
    ),
  getHistory: (limit = 20) =>
    request<HistoryResponse>(`${endpoints.workflowHistory}?limit=${limit}`),
}
