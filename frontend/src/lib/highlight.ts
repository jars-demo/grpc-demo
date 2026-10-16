// Build-time syntax highlighting with a light and a dark theme; CSS picks one (globals.css).
import { createHighlighter, type Highlighter } from 'shiki'

const LANGS = ['bash', 'powershell', 'python', 'json', 'toml', 'yaml', 'protobuf', 'text'] as const
const ALIASES: Record<string, string> = {
  sh: 'bash',
  shell: 'bash',
  console: 'bash',
  py: 'python',
  ps1: 'powershell',
  yml: 'yaml',
  proto: 'protobuf',
}

let highlighter: Promise<Highlighter> | null = null

export function resolveLang(lang: string | undefined): string {
  const resolved = ALIASES[lang ?? ''] ?? lang ?? 'text'
  return (LANGS as readonly string[]).includes(resolved) ? resolved : 'text'
}

export async function highlight(code: string, lang: string | undefined): Promise<string> {
  highlighter ??= createHighlighter({
    themes: ['github-light', 'github-dark-default'],
    langs: [...LANGS],
  })
  return (await highlighter).codeToHtml(code.replace(/\n$/, ''), {
    lang: resolveLang(lang),
    themes: { light: 'github-light', dark: 'github-dark-default' },
    defaultColor: 'light',
  })
}
