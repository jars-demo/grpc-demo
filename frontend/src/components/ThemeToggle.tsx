'use client'

import { useSyncExternalStore } from 'react'

type Choice = 'system' | 'light' | 'dark'
const KEY = 'grpc-demo:theme'
const ORDER: Choice[] = ['system', 'light', 'dark']

function read(): Choice {
  try {
    const value = localStorage.getItem(KEY)
    return value === 'light' || value === 'dark' ? value : 'system'
  } catch {
    return 'system'
  }
}

function apply(choice: Choice) {
  try {
    if (choice === 'system') localStorage.removeItem(KEY)
    else localStorage.setItem(KEY, choice)
  } catch {
    // storage blocked: the choice lasts for this page only
  }
  if (choice === 'system') delete document.documentElement.dataset.theme
  else document.documentElement.dataset.theme = choice
  window.dispatchEvent(new Event('grpc-demo:theme'))
}

function subscribe(callback: () => void) {
  window.addEventListener('grpc-demo:theme', callback)
  return () => window.removeEventListener('grpc-demo:theme', callback)
}

// Runs before first paint (inlined in <head>) so the page never flashes the wrong theme.
export const THEME_SCRIPT = `try{var t=localStorage.getItem('${KEY}');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}`

export function ThemeToggle() {
  const choice = useSyncExternalStore(subscribe, read, () => 'system' as Choice)
  const next = ORDER[(ORDER.indexOf(choice) + 1) % ORDER.length]
  return (
    <button
      type="button"
      onClick={() => apply(next)}
      className="rounded-md border border-line px-2.5 py-1 text-xs font-medium text-muted transition hover:text-text"
      aria-label={`Theme: ${choice}. Switch to ${next}.`}
      title={`Theme: ${choice}`}
    >
      {choice === 'system' ? 'Auto' : choice === 'light' ? 'Light' : 'Dark'}
    </button>
  )
}
