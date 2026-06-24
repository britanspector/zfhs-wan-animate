/** Format workflow/API error strings for display. */

export function formatWorkflowError(raw: string): string {
  if (!raw) return raw
  if (raw.startsWith('PoseAndFaceDetection') || raw.startsWith('ONNX')) return raw
  if (raw.includes('CUDNN_STATUS_SUBLIBRARY_VERSION_MISMATCH')) {
    return 'ONNX CUDA/cuDNN 版本不匹配。请重试；若仍失败请重启 ComfyUI。'
  }
  if (raw.includes('Failed to allocate memory for requested buffer of size')) {
    const m = raw.match(/size (\d+)/)
    if (m && Number(m[1]) > 1e12) {
      return '姿态检测 ONNX 在 GPU 上异常。请重试；若仍失败请重启 ComfyUI。'
    }
    return 'ONNX 显存不足，请降低分辨率/时长或重启 ComfyUI。'
  }
  const execErr = raw.match(/'execution_error',\s*(\{[^}]+\})/)
  if (execErr) {
    const node = raw.match(/'node_type':\s*'([^']+)'/)
    const msg = raw.match(/'exception_message':\s*"([^"]+)/)
    if (node && msg) {
      return `${node[1]}: ${msg[1].slice(0, 280)}`
    }
  }
  if (raw.length > 360) return `${raw.slice(0, 357)}...`
  return raw
}
