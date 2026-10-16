import type { ComponentProps, ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

import { rewriteHref, slugify } from '@/lib/parse'
import { DOCS, REPO_URL, SITE_URL } from '@/lib/site'

import { CodeBlock } from './CodeBlock'
import { Mermaid } from './Mermaid'

type HastNode = {
  type: string
  value?: string
  tagName?: string
  properties?: { className?: string[] }
  children?: HastNode[]
}

// Raw HTML in the Markdown is limited to what GitHub allows (details/summary for collapsible
// answers). Everything else - scripts, event handlers, styles - is stripped. HTML comments
// (the diagram markers) are dropped.
const SCHEMA = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), 'details', 'summary'],
}

const DOC_SLUGS = DOCS.map((d) => d.slug)

function textOf(node: HastNode | undefined): string {
  if (!node) return ''
  if (node.type === 'text') return node.value ?? ''
  return (node.children ?? []).map(textOf).join('')
}

function plain(children: ReactNode): string {
  if (typeof children === 'string' || typeof children === 'number') return String(children)
  if (Array.isArray(children)) return children.map(plain).join('')
  if (children && typeof children === 'object' && 'props' in children) {
    return plain((children.props as { children?: ReactNode }).children)
  }
  return ''
}

function Anchor({ href = '', children }: ComponentProps<'a'>) {
  const link = rewriteHref(href, REPO_URL, SITE_URL, DOC_SLUGS)
  return link.external ? (
    <a href={link.href} target="_blank" rel="noreferrer">
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  ) : (
    <a href={link.href}>{children}</a>
  )
}

function Pre({ node }: { node?: HastNode }) {
  const code = node?.children?.find((child) => child.tagName === 'code')
  const lang = code?.properties?.className?.find((c) => c.startsWith('language-'))?.slice(9)
  const source = textOf(code)
  if (lang === 'mermaid') {
    return <Mermaid source={source.trim()} label="Diagram - explained in the surrounding text" />
  }
  return <CodeBlock code={source} lang={lang} />
}

export function Markdown({ source }: { source: string }) {
  return (
    <div className="prose-workshop">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, SCHEMA]]}
        components={{
          pre: Pre as never,
          a: Anchor,
          table: ({ children }) => (
            <div className="table-wrap">
              <table>{children}</table>
            </div>
          ),
          h2: ({ children }) => <h2 id={slugify(plain(children))}>{children}</h2>,
          h3: ({ children }) => <h3 id={slugify(plain(children))}>{children}</h3>,
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  )
}
