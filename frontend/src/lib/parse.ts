// Pure parsing helpers for the repository's Markdown. No file system access here, so they are
// easy to test and safe to import anywhere.

export type Chapter = {
  slug: string // "05-first-grpc-call"
  number: string // "05"
  title: string // "Your First gRPC Call"
  minutes: number
  summary: string
}

export type Heading = { id: string; text: string }

const TITLE = /^#\s+(\d\d)\s+·\s+(.+)$/
const META = /^>\s*⏱\s*(\d+)\s+minutes?\s+·\s+(.+)$/

export class ChapterFormatError extends Error {}

// Every chapter starts with "# NN · Title" and "> ⏱ N minutes · summary". The site derives its
// navigation from these lines, so the Markdown stays the single source of truth.
export function parseChapter(slug: string, raw: string): { chapter: Chapter; body: string } {
  const lines = raw.replace(/\r\n/g, '\n').split('\n')
  const title = lines[0]?.match(TITLE)
  if (!title) throw new ChapterFormatError(`${slug}: first line must be "# NN · Title"`)
  const metaIndex = lines.findIndex((line) => META.test(line))
  if (metaIndex === -1) throw new ChapterFormatError(`${slug}: missing "> ⏱ N minutes · summary"`)
  const meta = lines[metaIndex].match(META)!
  if (!slug.startsWith(title[1])) throw new ChapterFormatError(`${slug}: number does not match`)

  const body = lines
    .filter((_, i) => i !== 0 && i !== metaIndex)
    .filter((line) => !line.startsWith('Next: ['))
    .join('\n')
    .trim()
  return {
    chapter: {
      slug,
      number: title[1],
      title: title[2].trim(),
      minutes: Number(meta[1]),
      summary: meta[2].trim(),
    },
    body,
  }
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[`*_]/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
}

// Level-2 headings outside code fences, for the table of contents.
export function headings(markdown: string): Heading[] {
  const result: Heading[] = []
  let inFence = false
  for (const line of markdown.split('\n')) {
    if (line.startsWith('```')) inFence = !inFence
    if (inFence) continue
    const match = line.match(/^##\s+(.+)$/)
    if (match) result.push({ id: slugify(match[1]), text: match[1].replace(/`/g, '') })
  }
  return result
}

// The Mermaid block that follows `<!-- diagram: id -->` in a document, so the landing page can
// render diagrams whose source lives in docs/architecture.md.
export function extractDiagram(markdown: string, id: string): string | null {
  const pattern = new RegExp(
    `<!--\\s*diagram:\\s*${id}\\s*-->\\s*\\n\`\`\`mermaid\\n([\\s\\S]*?)\\n\`\`\``,
  )
  return markdown.replace(/\r\n/g, '\n').match(pattern)?.[1] ?? null
}

// Strips the first "# Title" line of a document and returns it separately.
export function splitTitle(markdown: string): { title: string; body: string } {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  const first = lines[0]?.match(/^#\s+(.+)$/)
  return first
    ? { title: first[1].trim(), body: lines.slice(1).join('\n').trim() }
    : { title: '', body: markdown }
}

// Links inside the Markdown point at files in the repository, so they work on GitHub. On the
// site, chapter and doc links become site routes; anything else goes to GitHub.
export function rewriteHref(
  href: string,
  repoUrl: string,
  siteUrl: string,
  docSlugs: readonly string[],
): { href: string; external: boolean } {
  if (href.startsWith('#')) return { href, external: false }
  if (href.startsWith(siteUrl)) return { href: href.slice(siteUrl.length) || '/', external: false }
  if (/^(https?:|mailto:)/.test(href)) return { href, external: true }

  const [path, hash = ''] = href.split('#')
  const anchor = hash ? `#${hash}` : ''
  const file = path.split('/').pop() ?? ''

  const chapter = file.match(/^(\d\d-[a-z0-9-]+)\.md$/)
  if (chapter && (path === file || path.includes('workshop/'))) {
    return { href: `/workshop/${chapter[1]}/${anchor}`, external: false }
  }
  const doc = file.match(/^([a-z-]+)\.md$/)
  if (doc && docSlugs.includes(doc[1]) && (path.includes('docs/') || path === file)) {
    return { href: `/docs/${doc[1]}/${anchor}`, external: false }
  }
  // Any other repository path: resolve "../" and "./" against the repository root.
  const clean = path.replace(/^(\.\.\/)+/, '').replace(/^\.\//, '')
  return { href: `${repoUrl}/blob/main/${clean}${anchor}`, external: true }
}
