'use client'

import { useEffect, useId, useState } from 'react'

function isDark(): boolean {
  const chosen = document.documentElement.dataset.theme
  if (chosen) return chosen === 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

// Renders a Mermaid diagram from its source in the browser. Until it renders (or if it cannot),
// the source itself is shown, so the content is never lost.
export function Mermaid({ source, label }: { source: string; label: string }) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, '')
  const [svg, setSvg] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const [themeTick, setThemeTick] = useState(0)

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => setThemeTick((n) => n + 1)
    media.addEventListener('change', onChange)
    window.addEventListener('grpc-demo:theme', onChange)
    return () => {
      media.removeEventListener('change', onChange)
      window.removeEventListener('grpc-demo:theme', onChange)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    import('mermaid')
      .then(async ({ default: mermaid }) => {
        const dark = isDark()
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: 'base',
          fontFamily: 'inherit',
          themeVariables: {
            darkMode: dark,
            background: dark ? '#0e0e11' : '#ffffff',
            primaryColor: dark ? '#221f3a' : '#efedfd',
            primaryBorderColor: dark ? '#9d90f8' : '#6d5ae6',
            primaryTextColor: dark ? '#f4f4f5' : '#18181b',
            lineColor: dark ? '#a1a1aa' : '#71717a',
            secondaryColor: dark ? '#17171b' : '#f7f7fa',
            tertiaryColor: dark ? '#17171b' : '#f7f7fa',
            actorBkg: dark ? '#221f3a' : '#efedfd',
            actorBorder: dark ? '#9d90f8' : '#6d5ae6',
            noteBkgColor: dark ? '#17171b' : '#f7f7fa',
            noteBorderColor: dark ? '#2a2a30' : '#e4e4e7',
            noteTextColor: dark ? '#f4f4f5' : '#18181b',
            textColor: dark ? '#f4f4f5' : '#18181b',
            actorTextColor: dark ? '#f4f4f5' : '#18181b',
            signalTextColor: dark ? '#f4f4f5' : '#18181b',
            labelTextColor: dark ? '#f4f4f5' : '#18181b',
            signalColor: dark ? '#a1a1aa' : '#71717a',
            clusterBkg: dark ? '#17171b' : '#f7f7fa',
            clusterBorder: dark ? '#2a2a30' : '#e4e4e7',
            edgeLabelBackground: dark ? '#17171b' : '#ffffff',
            fontSize: '14px',
          },
        })
        const { svg } = await mermaid.render(`m${id}${themeTick}`, source)
        if (!cancelled) setSvg(svg)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [source, id, themeTick])

  return (
    <figure className="not-prose rounded-xl border border-line bg-bg p-4">
      {svg && !failed ? (
        <div
          role="img"
          aria-label={label}
          className="mermaid-figure overflow-x-auto"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : (
        <pre className="overflow-x-auto font-mono text-xs text-muted" aria-label={label}>
          {failed ? `Diagram could not be rendered. Source:\n\n${source}` : source}
        </pre>
      )}
      <figcaption className="mt-3 text-xs text-muted">{label}</figcaption>
    </figure>
  )
}
