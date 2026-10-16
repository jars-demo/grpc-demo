import type { Metadata } from 'next'

import { Footer } from '@/components/Footer'
import { Header } from '@/components/Header'
import { ChapterIndex, ProgressBar, ResetProgress } from '@/components/Progress'
import { listChapters } from '@/lib/content'

export const metadata: Metadata = {
  title: 'Workshop',
  description: 'All chapters of the gRPC & HTTPS workshop, with estimated durations.',
}

export default function WorkshopIndex() {
  const chapters = listChapters()
  const total = chapters.reduce((sum, c) => sum + c.minutes, 0)
  return (
    <>
      <Header current="/workshop/" />
      <main id="main" className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-semibold tracking-tight">Workshop</h1>
        <p className="mt-3 text-muted">
          {chapters.length} chapters, about {Math.round(total / 15) / 4} hours in total. Work in
          order: each chapter uses what the previous ones set up. Commands run in your terminal,
          from the repository root; this site never runs anything on your machine.
        </p>
        <div className="mt-8 space-y-3 rounded-xl border border-line bg-surface p-4">
          <ProgressBar slugs={chapters.map((c) => c.slug)} />
          <div className="flex justify-end">
            <ResetProgress />
          </div>
        </div>
        <div className="mt-8">
          <ChapterIndex chapters={chapters} />
        </div>
      </main>
      <Footer />
    </>
  )
}
