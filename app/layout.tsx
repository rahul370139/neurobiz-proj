import './globals.css'
import React from 'react'
import Providers from './providers'

export const metadata = {
  title: 'Supply Chain Analysis',
  description: 'Upload EDI and CSV files for AI-powered exception detection'
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-slate-900">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}


