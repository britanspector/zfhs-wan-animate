/** iframe-friendly deadlines: poll Date.now via rAF instead of setTimeout alone. */

export function waitUntil(deadlineMs: number): Promise<void> {
  return new Promise((resolve) => {
    const tick = () => {
      if (Date.now() >= deadlineMs) {
        resolve()
        return
      }
      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  })
}

export function sleepMs(ms: number): Promise<void> {
  return waitUntil(Date.now() + ms)
}

export type RaceResult<T> =
  | { ok: true; value: T }
  | { ok: false; reason: 'timeout' }

/** Resolve with value, or timeout via rAF deadline (survives iframe timer throttling better). */
export function raceWithDeadline<T>(
  promise: Promise<T>,
  timeoutMs: number,
): Promise<RaceResult<T>> {
  const deadline = Date.now() + timeoutMs
  return new Promise((resolve, reject) => {
    let settled = false
    promise.then(
      (value) => {
        if (settled) return
        settled = true
        resolve({ ok: true, value })
      },
      (err) => {
        if (settled) return
        settled = true
        reject(err)
      },
    )
    const tick = () => {
      if (settled) return
      if (Date.now() >= deadline) {
        settled = true
        resolve({ ok: false, reason: 'timeout' })
        return
      }
      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  })
}
