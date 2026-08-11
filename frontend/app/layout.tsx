import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Neraca Minyak',
  description:
    'Sistem forensik kehilangan rendemen kelapa sawit — menutup neraca dari gerbang sampai tangki.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  )
}
