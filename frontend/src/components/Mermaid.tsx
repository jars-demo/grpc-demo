'use client'

import { useEffect, useId, useState } from 'react'

function isDark(): boolean {
  return document.documentElement.dataset.theme === 'dark'
}

// Renders a Mermaid diagram from its source in the browser. Until it renders (or if it cannot),
// the source itself is shown, so the content is never lost.
export function Mermaid({ source, label }: { source: string; label: string }) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, '')
  const [svg, setSvg] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const [themeTick, setThemeTick] = useState(0)

  useEffect(() => {
    const onChange = () => setThemeTick((n) => n + 1)
    window.addEventListener('grpc-demo:theme', onChange)
    return () => window.removeEventListener('grpc-demo:theme', onChange)
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
            background: dark ? '#171717' : '#ffffff',
            primaryColor: dark ? '#1f1f1f' : '#f7f7f5',
            primaryBorderColor: dark ? '#4a4a47' : '#c9c9c4',
            primaryTextColor: dark ? '#ececea' : '#1a1a1a',
            lineColor: dark ? '#7a7a76' : '#8a8a86',
            secondaryColor: dark ? '#1f1f1f' : '#f7f7f5',
            tertiaryColor: dark ? '#1f1f1f' : '#ffffff',
            actorBkg: dark ? '#1f1f1f' : '#f7f7f5',
            actorBorder: dark ? '#4a4a47' : '#c9c9c4',
            noteBkgColor: dark ? '#242423' : '#ffffff',
            noteBorderColor: dark ? '#2e2e2c' : '#e7e7e3',
            noteTextColor: dark ? '#ececea' : '#1a1a1a',
            textColor: dark ? '#ececea' : '#1a1a1a',
            actorTextColor: dark ? '#ececea' : '#1a1a1a',
            signalTextColor: dark ? '#ececea' : '#1a1a1a',
            labelTextColor: dark ? '#ececea' : '#1a1a1a',
            signalColor: dark ? '#7a7a76' : '#8a8a86',
            clusterBkg: dark ? '#1b1b1b' : '#fbfbfa',
            clusterBorder: dark ? '#2e2e2c' : '#e7e7e3',
            edgeLabelBackground: dark ? '#171717' : '#ffffff',
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
