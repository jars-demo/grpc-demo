// Server-only: reads the workshop chapters (workshop/*.md), docs (docs/*.md) and challenge
// scenarios from the repository at build time. Nothing here ships to the browser.
import { readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'

import { type Chapter, parseChapter, splitTitle } from './parse'
import type { DocSlug } from './site'

// Next runs from frontend/; the content lives one level up.
export const REPO_ROOT = path.resolve(process.cwd(), '..')

function read(...parts: string[]): string {
  return readFileSync(path.join(REPO_ROOT, ...parts), 'utf8').replace(/\r\n/g, '\n')
}

export function listChapters(): Chapter[] {
  return readdirSync(path.join(REPO_ROOT, 'workshop'))
    .filter((name) => /^\d\d-[a-z0-9-]+\.md$/.test(name))
    .sort()
    .map((name) => {
      const slug = name.replace(/\.md$/, '')
      return parseChapter(slug, read('workshop', name)).chapter
    })
}

export function loadChapter(slug: string): { chapter: Chapter; body: string } {
  return parseChapter(slug, read('workshop', `${slug}.md`))
}

export function loadDoc(slug: DocSlug): { title: string; body: string } {
  return splitTitle(read('docs', `${slug}.md`))
}

export function readRepoFile(...parts: string[]): string {
  return read(...parts)
}

// Scenario titles come from the first comment line of each broken profile template:
// "# Scenario 01 - The certificate nobody trusts"
export function listScenarios(): { number: string; title: string }[] {
  return readdirSync(path.join(REPO_ROOT, 'challenge', 'scenarios'))
    .filter((name) => /^\d\d\.toml$/.test(name))
    .sort()
    .map((name) => {
      const first = read('challenge', 'scenarios', name).split('\n')[0]
      const match = first.match(/^#\s*Scenario\s+(\d\d)\s+-\s+(.+)$/)
      return { number: match?.[1] ?? name.slice(0, 2), title: match?.[2]?.trim() ?? name }
    })
}
