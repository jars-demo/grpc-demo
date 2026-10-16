import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ChapterIndex, MarkComplete, ProgressBar, ResetProgress } from '@/components/Progress'
import type { Chapter } from '@/lib/parse'
import { readProgress, STORAGE_KEY, writeProgress } from '@/lib/progress'

const CHAPTERS: Chapter[] = [
  { slug: '00-overview', number: '00', title: 'Overview', minutes: 10, summary: 'Setup and goals' },
  {
    slug: '08-enable-tls',
    number: '08',
    title: 'Enable TLS',
    minutes: 15,
    summary: 'Secure the connection',
  },
  {
    slug: '10-mutual-tls',
    number: '10',
    title: 'Mutual TLS',
    minutes: 15,
    summary: 'Client certificates',
  },
]
const SLUGS = CHAPTERS.map((c) => c.slug)

beforeEach(() => localStorage.clear())
afterEach(cleanup)

describe('progress storage', () => {
  it('round-trips completed chapters, de-duplicated and sorted', () => {
    writeProgress(['10-mutual-tls', '00-overview', '10-mutual-tls'])
    expect(readProgress()).toEqual(['00-overview', '10-mutual-tls'])
  })

  it('treats corrupted storage as empty instead of crashing', () => {
    localStorage.setItem(STORAGE_KEY, '{not json')
    expect(readProgress()).toEqual([])
  })

  it('ignores non-string entries', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(['00-overview', 3, null]))
    expect(readProgress()).toEqual(['00-overview'])
  })

  it('keeps working when storage throws', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(() => writeProgress(['00-overview'])).not.toThrow()
    spy.mockRestore()
  })
})

describe('MarkComplete', () => {
  it('marks a chapter complete, persists it, and updates the progress bar', () => {
    render(
      <>
        <ProgressBar slugs={SLUGS} />
        <MarkComplete slug="08-enable-tls" />
      </>,
    )
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('0')

    fireEvent.click(screen.getByRole('button', { name: /mark chapter as complete/i }))

    expect(readProgress()).toEqual(['08-enable-tls'])
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('33')
    expect(screen.getByRole('button', { pressed: true })).toBeTruthy()
  })

  it('un-marks a completed chapter', () => {
    writeProgress(['08-enable-tls'])
    render(<MarkComplete slug="08-enable-tls" />)

    fireEvent.click(screen.getByRole('button', { name: /mark as not done/i }))

    expect(readProgress()).toEqual([])
  })

  it('reflects progress written in another tab (storage event)', () => {
    render(<ProgressBar slugs={SLUGS} />)
    act(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(SLUGS))
      window.dispatchEvent(new StorageEvent('storage', { key: STORAGE_KEY }))
    })
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('100')
  })
})

describe('ResetProgress', () => {
  it('is hidden when there is nothing to reset', () => {
    const { container } = render(<ResetProgress />)
    expect(container.textContent).toBe('')
  })

  it('asks for confirmation, then clears progress', () => {
    writeProgress(['00-overview'])
    render(<ResetProgress />)

    fireEvent.click(screen.getByRole('button', { name: 'Reset progress' }))
    fireEvent.click(screen.getByRole('button', { name: 'Yes, reset' }))

    expect(readProgress()).toEqual([])
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
  })

  it('can be cancelled', () => {
    writeProgress(['00-overview'])
    render(<ResetProgress />)

    fireEvent.click(screen.getByRole('button', { name: 'Reset progress' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(readProgress()).toEqual(['00-overview'])
  })
})

describe('ChapterIndex', () => {
  it('lists every chapter with a link to its page', () => {
    render(<ChapterIndex chapters={CHAPTERS} />)
    expect(screen.getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual([
      '/workshop/00-overview/',
      '/workshop/08-enable-tls/',
      '/workshop/10-mutual-tls/',
    ])
  })

  it('filters by title and summary, case-insensitively', () => {
    render(<ChapterIndex chapters={CHAPTERS} />)

    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'TLS' } })

    expect(screen.getAllByRole('link')).toHaveLength(2)
  })

  it('shows an empty state with a way back when nothing matches', () => {
    render(<ChapterIndex chapters={CHAPTERS} />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'kubernetes' } })

    expect(screen.getByText(/No chapter matches/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /clear the filter/i }))
    expect(screen.getAllByRole('link')).toHaveLength(3)
  })

  it('marks completed chapters for screen readers', () => {
    writeProgress(['10-mutual-tls'])
    render(<ChapterIndex chapters={CHAPTERS} />)
    expect(screen.getAllByText('completed')).toHaveLength(1)
  })
})
