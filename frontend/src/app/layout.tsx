import { GeistMono } from 'geist/font/mono'
import { GeistSans } from 'geist/font/sans'
import type { Metadata, Viewport } from 'next'
import type { ReactNode } from 'react'

import { THEME_SCRIPT } from '@/components/ThemeToggle'
import { DESCRIPTION, MAINTAINER, SITE_URL, TAGLINE, TITLE } from '@/lib/site'

import './globals.css'

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: `${TITLE} — ${TAGLINE}`, template: `%s · ${TITLE}` },
  description: DESCRIPTION,
  authors: [{ name: MAINTAINER.name, url: MAINTAINER.url }],
  openGraph: {
    type: 'website',
    url: SITE_URL,
    siteName: TITLE,
    title: `${TITLE} — ${TAGLINE}`,
    description: DESCRIPTION,
  },
  twitter: { card: 'summary', title: `${TITLE} — ${TAGLINE}`, description: DESCRIPTION },
}

export const viewport: Viewport = {
  themeColor: '#ffffff',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-screen">{children}</body>
    </html>
  )
}
