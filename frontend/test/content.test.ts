// Tests against the real workshop/ and docs/ files: the site must be able to render every chapter,
// and every chapter must have the structure the curriculum promises.
import { readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { extractDiagram, headings, parseChapter, rewriteHref } from '@/lib/parse'

const ROOT = path.resolve(__dirname, '..', '..')
const files = readdirSync(path.join(ROOT, 'workshop'))
  .filter((f) => /^\d\d-.*\.md$/.test(f))
  .sort()
const read = (...p: string[]) => readFileSync(path.join(ROOT, ...p), 'utf8')

const REQUIRED_SECTIONS = [
  'learning-objectives',
  'prerequisites',
  'exercise',
  'what-just-happened',
  'knowledge-check',
  'done-when',
]

describe('workshop chapters', () => {
  it('number between 12 and 15 chapters, numbered consecutively from 00', () => {
    expect(files.length).toBeGreaterThanOrEqual(12)
    expect(files.length).toBeLessThanOrEqual(15)
    files.forEach((file, i) => expect(file.slice(0, 2)).toBe(String(i).padStart(2, '0')))
  })

  it.each(files)('%s parses with a title, duration and summary', (file) => {
    const { chapter } = parseChapter(file.replace(/\.md$/, ''), read('workshop', file))
    expect(chapter.title.length).toBeGreaterThan(3)
    expect(chapter.minutes).toBeGreaterThanOrEqual(5)
    expect(chapter.minutes).toBeLessThanOrEqual(40)
    expect(chapter.summary.length).toBeGreaterThan(10)
  })

  it.each(files)('%s has every required section', (file) => {
    const { body } = parseChapter(file.replace(/\.md$/, ''), read('workshop', file))
    const ids = headings(body).map((h) => h.id)
    for (const section of REQUIRED_SECTIONS) {
      expect(
        ids.some((id) => id.startsWith(section)),
        `${file}: ${section}`,
      ).toBe(true)
    }
    expect(
      ids.some((id) => id.startsWith('common-failure')),
      `${file}: common failure`,
    ).toBe(true)
    expect(
      ids.some((id) => id.startsWith('concept')),
      `${file}: concept`,
    ).toBe(true)
  })

  it.each(files)('%s links only to chapters and files that exist', (file) => {
    const links = [...read('workshop', file).matchAll(/\]\(([^)\s]+)\)/g)].map((m) => m[1])
    for (const link of links.filter((l) => !/^(https?:|mailto:|#)/.test(l))) {
      const target = path.resolve(ROOT, 'workshop', link.split('#')[0])
      expect(() => readFileSync(target), `${file} -> ${link}`).not.toThrow()
    }
  })

  it('takes between 2 and 4 hours in total', () => {
    const total = files.reduce(
      (sum, f) => sum + parseChapter(f.replace(/\.md$/, ''), read('workshop', f)).chapter.minutes,
      0,
    )
    expect(total).toBeGreaterThanOrEqual(120)
    expect(total).toBeLessThanOrEqual(240)
  })
})

describe('parseChapter', () => {
  it('drops the title, meta line and trailing Next link from the body', () => {
    const raw =
      '# 03 · Thing\n\n> ⏱ 15 minutes · Summary here.\n\n## Concept\n\nText\n\nNext: [04](04-x.md)\n'
    const { chapter, body } = parseChapter('03-thing', raw)
    expect(chapter).toEqual({
      slug: '03-thing',
      number: '03',
      title: 'Thing',
      minutes: 15,
      summary: 'Summary here.',
    })
    expect(body).toBe('## Concept\n\nText')
  })

  it('rejects a chapter without a meta line', () => {
    expect(() => parseChapter('03-thing', '# 03 · Thing\n\nNo meta')).toThrow(/minutes/)
  })
})

describe('headings', () => {
  it('ignores headings inside code fences', () => {
    expect(headings('## Real\n```bash\n## not a heading\n```\n## `Code` title')).toEqual([
      { id: 'real', text: 'Real' },
      { id: 'code-title', text: 'Code title' },
    ])
  })
})

describe('architecture diagrams', () => {
  const architecture = read('docs', 'architecture.md')
  it.each(['rest-flow', 'tls-trust', 'grpc-flow', 'mtls-flow', 'compose-topology'])(
    '%s is present as Mermaid source',
    (id) => {
      const source = extractDiagram(architecture, id)
      expect(source).toMatch(/^(sequenceDiagram|flowchart)/)
    },
  )

  it('returns null for an unknown diagram', () => {
    expect(extractDiagram(architecture, 'nope')).toBeNull()
  })
})

describe('rewriteHref', () => {
  const repo = 'https://github.com/jars-demo/grpc-demo'
  const site = 'https://grpc.jishanahmed.in'
  const docs = ['architecture', 'security', 'troubleshooting', 'commands']
  const rewrite = (href: string) => rewriteHref(href, repo, site, docs)

  it('turns chapter files into chapter routes', () => {
    expect(rewrite('05-first-grpc-call.md')).toEqual({
      href: '/workshop/05-first-grpc-call/',
      external: false,
    })
    expect(rewrite('../workshop/11-debugging-clinic.md#concept')).toEqual({
      href: '/workshop/11-debugging-clinic/#concept',
      external: false,
    })
  })

  it('turns docs into doc routes and keeps anchors', () => {
    expect(rewrite('../docs/security.md#before-production').href).toBe(
      '/docs/security/#before-production',
    )
    expect(rewrite('security.md').href).toBe('/docs/security/')
  })

  it('sends other repository files to GitHub', () => {
    expect(rewrite('../CONTRIBUTING.md')).toEqual({
      href: `${repo}/blob/main/CONTRIBUTING.md`,
      external: true,
    })
  })

  it('keeps external and in-page links', () => {
    expect(rewrite('https://example.com/x')).toEqual({
      href: 'https://example.com/x',
      external: true,
    })
    expect(rewrite('#top')).toEqual({ href: '#top', external: false })
    expect(rewrite(`${site}/workshop/`)).toEqual({ href: '/workshop/', external: false })
  })
})
