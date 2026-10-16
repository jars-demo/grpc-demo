'use client'

import { useSyncExternalStore } from 'react'

// Light by default. Dark only when the visitor picks it; the choice is remembered in this browser.
type Choice = 'light' | 'dark'
const KEY = 'grpc-demo:theme'

function read(): Choice {
  try {
    return localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

function apply(choice: Choice) {
  try {
    if (choice === 'light') localStorage.removeItem(KEY)
    else localStorage.setItem(KEY, choice)
  } catch {
    // storage blocked: the choice lasts for this page only
  }
  if (choice === 'light') delete document.documentElement.dataset.theme
  else document.documentElement.dataset.theme = choice
  window.dispatchEvent(new Event('grpc-demo:theme'))
}

function subscribe(callback: () => void) {
  window.addEventListener('grpc-demo:theme', callback)
  return () => window.removeEventListener('grpc-demo:theme', callback)
}

// Runs before first paint (inlined in <head>) so the page never flashes the wrong theme.
export const THEME_SCRIPT = `try{if(localStorage.getItem('${KEY}')==='dark')document.documentElement.dataset.theme='dark'}catch(e){}`

export function ThemeToggle() {
  const choice = useSyncExternalStore(subscribe, read, () => 'light' as Choice)
  const next: Choice = choice === 'light' ? 'dark' : 'light'
  return (
    <button
      type="button"
      onClick={() => apply(next)}
      className="rounded-md border border-line px-2.5 py-1 text-xs font-medium text-muted transition hover:text-text"
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      {choice === 'light' ? 'Dark' : 'Light'}
    </button>
  )
}
