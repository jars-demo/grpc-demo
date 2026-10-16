'use client'

import { useState } from 'react'

import type { Chapter } from '@/lib/parse'
import { useProgress } from '@/lib/progress'

export function ProgressBar({ slugs }: { slugs: string[] }) {
  const { completed } = useProgress()
  const done = completed.filter((slug) => slugs.includes(slug)).length
  const percent = slugs.length ? Math.round((done / slugs.length) * 100) : 0
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs font-medium text-muted">
        <span id="progress-label">Your progress (saved in this browser only)</span>
        <span>
          {done}/{slugs.length} chapters
        </span>
      </div>
      <div
        role="progressbar"
        aria-labelledby="progress-label"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-line"
      >
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}

export function MarkComplete({ slug }: { slug: string }) {
  const { completed, toggle } = useProgress()
  const done = completed.includes(slug)
  return (
    <button
      type="button"
      onClick={() => toggle(slug)}
      aria-pressed={done}
      className={`rounded-lg border px-4 py-2 text-sm font-medium transition ${
        done
          ? 'border-accent bg-accent-soft text-accent'
          : 'border-line text-text hover:border-accent hover:text-accent'
      }`}
    >
      {done ? 'Completed - mark as not done' : 'Mark chapter as complete'}
    </button>
  )
}

export function ResetProgress() {
  const { completed, reset } = useProgress()
  const [confirming, setConfirming] = useState(false)
  if (!completed.length) return null
  return confirming ? (
    <span className="flex items-center gap-2 text-xs">
      <span className="text-muted">Clear all progress?</span>
      <button
        type="button"
        className="rounded-md border border-line px-2 py-1 font-medium text-bad"
        onClick={() => {
          reset()
          setConfirming(false)
        }}
      >
        Yes, reset
      </button>
      <button
        type="button"
        className="rounded-md px-2 py-1 text-muted hover:text-text"
        onClick={() => setConfirming(false)}
      >
        Cancel
      </button>
    </span>
  ) : (
    <button
      type="button"
      className="text-xs text-muted underline underline-offset-4 hover:text-text"
      onClick={() => setConfirming(true)}
    >
      Reset progress
    </button>
  )
}

function Check({ done }: { done: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border text-[10px] ${
        done ? 'border-text bg-text text-bg' : 'border-line text-transparent'
      }`}
    >
      ✓
    </span>
  )
}

// The chapter list with a filter box, used on /workshop/.
export function ChapterIndex({ chapters }: { chapters: Chapter[] }) {
  const { completed } = useProgress()
  const [query, setQuery] = useState('')
  const q = query.trim().toLowerCase()
  const visible = chapters.filter(
    (c) => !q || `${c.number} ${c.title} ${c.summary}`.toLowerCase().includes(q),
  )
  return (
    <div className="space-y-4">
      <label className="block">
        <span className="sr-only">Filter chapters</span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter chapters, e.g. tls, streaming, deadline"
          className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm placeholder:text-muted"
        />
      </label>
      {visible.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line p-6 text-center text-sm text-muted">
          No chapter matches &ldquo;{query}&rdquo;.{' '}
          <button type="button" className="underline" onClick={() => setQuery('')}>
            Clear the filter
          </button>
        </p>
      ) : (
        <ol className="divide-y divide-line overflow-hidden rounded-xl border border-line">
          {visible.map((c) => {
            const done = completed.includes(c.slug)
            return (
              <li key={c.slug}>
                <a
                  href={`/workshop/${c.slug}/`}
                  className="flex items-center gap-4 px-4 py-3 transition hover:bg-surface"
                >
                  <span className="w-6 font-mono text-xs text-muted">{c.number}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{c.title}</span>
                    <span className="block truncate text-sm text-muted">{c.summary}</span>
                  </span>
                  <span className="hidden text-xs text-muted sm:block">{c.minutes} min</span>
                  <Check done={done} />
                  <span className="sr-only">{done ? 'completed' : 'not completed'}</span>
                </a>
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}

// The compact chapter list beside a chapter, with the current one highlighted.
export function ChapterSidebar({ chapters, current }: { chapters: Chapter[]; current: string }) {
  const { completed } = useProgress()
  return (
    <ol className="space-y-0.5 text-sm">
      {chapters.map((c) => {
        const active = c.slug === current
        return (
          <li key={c.slug}>
            <a
              href={`/workshop/${c.slug}/`}
              aria-current={active ? 'page' : undefined}
              className={`flex items-center gap-2 rounded-md px-2 py-1.5 transition ${
                active ? 'bg-accent-soft font-medium text-accent' : 'text-muted hover:text-text'
              }`}
            >
              <span className="w-5 font-mono text-xs">{c.number}</span>
              <span className="flex-1 truncate">{c.title}</span>
              {completed.includes(c.slug) && (
                <span className="text-xs text-accent" aria-label="completed">
                  ✓
                </span>
              )}
            </a>
          </li>
        )
      })}
    </ol>
  )
}
