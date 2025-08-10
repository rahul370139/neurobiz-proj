"use client"
import React from 'react'
import { UploadProvider } from '@/lib/upload-context'

export default function Providers({ children }: { children: React.ReactNode }) {
  return <UploadProvider>{children}</UploadProvider>
}


