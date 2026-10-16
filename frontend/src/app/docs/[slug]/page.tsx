import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

import { Footer } from '@/components/Footer'
import { Header } from '@/components/Header'
import { Markdown } from '@/components/Markdown'
import { loadDoc } from '@/lib/content'
import { headings } from '@/lib/parse'
import { DOCS, type DocSlug, REPO_URL } from '@/lib/site'

type Params = { slug: string }

export const dynamicParams = false

export function generateStaticParams(): Params[] {
  return DOCS.map((d) => ({ slug: d.slug }))
}

function find(slug: string) {
  return DOCS.find((d) => d.slug === slug)
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const doc = find((await params).slug)
  return doc ? { title: doc.title } : {}
}

export default async function DocPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params
  const doc = find(slug)
  if (!doc) notFound()
  const { title, body } = loadDoc(doc.slug as DocSlug)
  const toc = headings(body)

  return (
    <>
      <Header current={`/docs/${doc.slug}/`} />
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-10 sm:px-6 lg:grid-cols-[12rem_minmax(0,1fr)]">
        <aside className="hidden lg:block">
          <nav aria-label="Reference" className="sticky top-20 space-y-1 text-sm">
            <p className="mb-2 font-medium">Reference</p>
            {DOCS.map((d) => (
              <a
                key={d.slug}
                href={`/docs/${d.slug}/`}
                aria-current={d.slug === doc.slug ? 'page' : undefined}
                className="block rounded-md px-2 py-1.5 text-muted hover:text-text aria-[current=page]:bg-accent-soft aria-[current=page]:font-medium aria-[current=page]:text-accent"
              >
                {d.title}
              </a>
            ))}
            {toc.length > 0 && (
              <>
                <p className="mb-2 mt-6 font-medium">On this page</p>
                {toc.map((h) => (
                  <a
                    key={h.id}
                    href={`#${h.id}`}
                    className="block px-2 py-1 text-muted hover:text-text"
                  >
                    {h.text}
                  </a>
                ))}
              </>
            )}
          </nav>
        </aside>
        <main id="main" className="min-w-0">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
          <div className="mt-8">
            <Markdown source={body} />
          </div>
          <p className="mt-12 border-t border-line pt-6 text-sm text-muted">
            Source:{' '}
            <a
              className="underline underline-offset-4"
              href={`${REPO_URL}/blob/main/docs/${doc.slug}.md`}
            >
              docs/{doc.slug}.md
            </a>
          </p>
        </main>
      </div>
      <Footer />
    </>
  )
}
