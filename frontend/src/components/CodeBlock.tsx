import { highlight, resolveLang } from '@/lib/highlight'

import { CopyButton } from './CopyButton'

// The label tells the reader WHERE a block belongs: a terminal command, or output to compare with.
const LABELS: Record<string, string> = {
  bash: 'Terminal',
  powershell: 'PowerShell',
  python: 'Python',
  json: 'JSON',
  toml: 'TOML',
  yaml: 'YAML',
  protobuf: 'Protocol Buffers',
  text: 'Output',
}

export async function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  const html = await highlight(code, lang)
  const resolved = resolveLang(lang)
  const isCommand = resolved === 'bash' || resolved === 'powershell'
  return (
    <figure className="not-prose overflow-hidden rounded-xl border border-line bg-code">
      <figcaption className="flex items-center justify-between border-b border-line px-3 py-1.5 text-xs text-muted">
        <span>
          {LABELS[resolved] ?? resolved}
          {isCommand && <span className="sr-only"> command to run yourself</span>}
        </span>
        <CopyButton text={code.replace(/\n$/, '')} />
      </figcaption>
      <div className="code-body" dangerouslySetInnerHTML={{ __html: html }} />
    </figure>
  )
}
