/** Default sample basenames under ComfyUI/input (aligned with config/default.yaml). */
export const SAMPLE_IMAGE = 'C罗.jpg'
export const SAMPLE_VIDEO = '世界杯手势舞.mp4'

export function basenameFromPath(path?: string, fallback = ''): string {
  if (!path) return fallback
  const parts = path.split(/[/\\]/)
  return parts[parts.length - 1] || fallback
}
