import nextCoreWebVitals from 'eslint-config-next/core-web-vitals'
import nextTypescript from 'eslint-config-next/typescript'

const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  { ignores: ['.next/**', 'out/**', 'node_modules/**', 'next-env.d.ts', 'coverage/**'] },
  {
    rules: {
      // Plain <a> is deliberate: a static export where every link must work without JavaScript.
      '@next/next/no-html-link-for-pages': 'off',
    },
  },
]

export default config
