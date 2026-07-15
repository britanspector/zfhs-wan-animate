const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export const endpoints = {
  health: `${API_BASE}/api/health`,
  gpuInfo: `${API_BASE}/api/gpu/info`,
  comfyStatus: `${API_BASE}/api/comfy/status`,
  comfyStart: `${API_BASE}/api/comfy/start`,
  comfyStop: `${API_BASE}/api/comfy/stop`,
  comfyInterrupt: `${API_BASE}/api/comfy/proxy/interrupt`,
  warmupStatus: `${API_BASE}/api/warmup/status`,
  comfyUpload: `${API_BASE}/api/comfy/upload/file`,
  comfyView: `${API_BASE}/api/comfy/view`,
  workflowConfig: (id: string) => `${API_BASE}/api/workflow/config/${encodeURIComponent(id)}`,
  workflowGenerate: `${API_BASE}/api/workflow/generate`,
  workflowValidateInput: `${API_BASE}/api/workflow/validate-input`,
  workflowDiagnosticLog: `${API_BASE}/api/workflow/diagnostic-log`,
  workflowResult: `${API_BASE}/api/workflow/result`,
  workflowProgress: `${API_BASE}/api/workflow/progress`,
  workflowHistory: `${API_BASE}/api/workflow/history`,
  wsProxy: (clientId: string) => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}${API_BASE}/api/comfy/proxy/ws?clientId=${encodeURIComponent(clientId)}`
  },
}

export function buildViewUrl(filename: string, type = 'input', subfolder = ''): string {
  const params = new URLSearchParams({ filename, type })
  if (subfolder) params.set('subfolder', subfolder)
  return `${endpoints.comfyView}?${params.toString()}`
}
