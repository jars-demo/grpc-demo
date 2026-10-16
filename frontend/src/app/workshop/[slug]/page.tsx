import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

import { Footer } from '@/components/Footer'
import { Header } from '@/components/Header'
import { Markdown } from '@/components/Markdown'
import { ChapterSidebar, MarkComplete, ProgressBar } from '@/components/Progress'
import { listChapters, loadChapter } from '@/lib/content'
import { headings } from '@/lib/parse'
import { REPO_URL } from '@/lib/site'

type Params = { slug: string }

export const dynamicParams = false

export function generateStaticParams(): Params[] {
  return listChapters().map((c) => ({ slug: c.slug }))
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params
  const chapter = listChapters().find((c) => c.slug === slug)
  if (!chapter) return {}
  return { title: `${chapter.number} · ${chapter.title}`, description: chapter.summary }
}

export default async function ChapterPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params
  const chapters = listChapters()
  const index = chapters.findIndex((c) => c.slug === slug)
  if (index === -1) notFound()
  const { chapter, body } = loadChapter(slug)
  const previous = chapters[index - 1]
  const next = chapters[index + 1]
  const toc = headings(body)

  return (
    <>
      <Header current="/workshop/" />
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-10 sm:px-6 lg:grid-cols-[14rem_minmax(0,1fr)] xl:grid-cols-[14rem_minmax(0,1fr)_12rem]">
        <aside className="hidden lg:block">
          <nav aria-label="Chapters" className="sticky top-20 space-y-4">
            <ProgressBar slugs={chapters.map((c) => c.slug)} />
            <ChapterSidebar chapters={chapters} current={slug} />
          </nav>
        </aside>

        <main id="main" className="min-w-0">
          <nav aria-label="Breadcrumb" className="text-sm text-muted">
            <a href="/workshop/" className="hover:text-text">
              Workshop
            </a>{' '}
            / Chapter {chapter.number}
          </nav>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
            {chapter.title}
          </h1>
          <p className="mt-2 text-muted">
            <span className="font-medium text-text">{chapter.minutes} minutes</span> ·{' '}
            {chapter.summary}
          </p>

          {toc.length > 0 && (
            <details className="mt-6 rounded-lg border border-line p-3 xl:hidden">
              <summary className="cursor-pointer text-sm font-medium">On this page</summary>
              <ul className="mt-2 space-y-1 text-sm">
                {toc.map((h) => (
                  <li key={h.id}>
                    <a href={`#${h.id}`} className="text-muted hover:text-text">
                      {h.text}
                    </a>
                  </li>
                ))}
              </ul>
            </details>
          )}

          <div className="mt-8">
            <Markdown source={body} />
          </div>

          <div className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-6">
            <MarkComplete slug={slug} />
            <a
              href={`${REPO_URL}/blob/main/workshop/${slug}.md`}
              className="text-sm text-muted underline underline-offset-4 hover:text-text"
            >
              View this chapter on GitHub
            </a>
          </div>

          <nav aria-label="Chapter navigation" className="mt-8 grid gap-3 sm:grid-cols-2">
            {previous ? (
              <a
                href={`/workshop/${previous.slug}/`}
                rel="prev"
                className="rounded-xl border border-line p-4 transition hover:border-accent"
              >
                <span className="text-xs text-muted">Previous</span>
                <span className="block font-medium">
                  {previous.number} · {previous.title}
                </span>
              </a>
            ) : (
              <span />
            )}
            {next && (
              <a
                href={`/workshop/${next.slug}/`}
                rel="next"
                className="rounded-xl border border-line p-4 text-right transition hover:border-accent"
              >
                <span className="text-xs text-muted">Next</span>
                <span className="block font-medium">
                  {next.number} · {next.title}
                </span>
              </a>
            )}
          </nav>
        </main>

        {toc.length > 0 && (
          <aside className="hidden xl:block">
            <nav aria-label="On this page" className="sticky top-20 text-sm">
              <p className="mb-2 font-medium">On this page</p>
              <ul className="space-y-1.5 border-l border-line">
                {toc.map((h) => (
                  <li key={h.id}>
                    <a
                      href={`#${h.id}`}
                      className="-ml-px block border-l border-transparent pl-3 text-muted hover:border-accent hover:text-text"
                    >
                      {h.text}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </aside>
        )}
      </div>
      <Footer />
    </>
  )
}
