/** Normalize API media URLs for public gateway / same-origin playback. */
export function normalizeMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null
  if (url.startsWith('/')) return url
  if (url.startsWith('http://127.0.0.1') || url.startsWith('http://localhost')) {
    try {
      const parsed = new URL(url)
      return parsed.pathname + parsed.search
    } catch {
      return url
    }
  }
  return url
}
