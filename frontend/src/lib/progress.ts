'use client'

// Workshop progress, stored only in this browser's localStorage. No account, no server.
import { useCallback, useSyncExternalStore } from 'react'

export const STORAGE_KEY = 'grpc-demo:progress:v1'
const EVENT = 'grpc-demo:progress'

export function readProgress(): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    return Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : []
  } catch {
    return [] // storage blocked or corrupted: start empty, never crash
  }
}

export function writeProgress(slugs: string[]): void {
  try {
    if (slugs.length) localStorage.setItem(STORAGE_KEY, JSON.stringify([...new Set(slugs)].sort()))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Storage blocked (private mode, policy): progress is not remembered; everything else works.
  }
  window.dispatchEvent(new Event(EVENT))
}

function subscribe(callback: () => void): () => void {
  window.addEventListener(EVENT, callback)
  window.addEventListener('storage', callback) // other tabs
  return () => {
    window.removeEventListener(EVENT, callback)
    window.removeEventListener('storage', callback)
  }
}

let cached = '[]'
function snapshot(): string {
  const next = JSON.stringify(readProgress())
  if (next !== cached) cached = next
  return cached
}

export function useProgress() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => '[]')
  const completed = JSON.parse(raw) as string[]
  const toggle = useCallback((slug: string) => {
    const current = readProgress()
    writeProgress(current.includes(slug) ? current.filter((s) => s !== slug) : [...current, slug])
  }, [])
  const reset = useCallback(() => writeProgress([]), [])
  return { completed, toggle, reset }
}
