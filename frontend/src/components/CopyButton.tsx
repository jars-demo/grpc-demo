'use client'

import { useState } from 'react'

export function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')

  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setState('copied')
    } catch {
      setState('failed') // clipboard blocked (insecure context or permissions)
    }
    setTimeout(() => setState('idle'), 1600)
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-md px-2 py-0.5 text-xs font-medium text-muted transition hover:bg-accent-soft hover:text-text"
      aria-label={`${label} to clipboard`}
    >
      <span aria-live="polite">
        {state === 'copied' ? 'Copied' : state === 'failed' ? 'Select & copy' : label}
      </span>
    </button>
  )
}
