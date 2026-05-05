import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'

/** Static metadata displayed by Next.js for every app route. */
export const metadata: Metadata = {
  title: 'n8n Inquiry Platform',
  description: 'Multi-agent customer inquiry automation dashboard',
}

/**
 * Root HTML layout that installs global styles and providers.
 *
 * @param props - Layout props.
 * @param props.children - Route content selected by Next.js.
 * @returns HTML document shell for the app router.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
