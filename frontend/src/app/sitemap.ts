import type { MetadataRoute } from 'next'

import { listChapters } from '@/lib/content'
import { DOCS, SITE_URL } from '@/lib/site'

export const dynamic = 'force-static'

export default function sitemap(): MetadataRoute.Sitemap {
  const paths = [
    '/',
    '/workshop/',
    ...listChapters().map((c) => `/workshop/${c.slug}/`),
    ...DOCS.map((d) => `/docs/${d.slug}/`),
  ]
  return paths.map((path) => ({ url: `${SITE_URL}${path}` }))
}
