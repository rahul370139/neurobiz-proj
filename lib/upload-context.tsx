"use client"
import React, { createContext, useContext, useState } from 'react'

export type UploadResponse = { message: string; files_processed: string[]; next_step: string; success?: boolean }

type UploadContextValue = {
  edi850: File | null
  edi856: File | null
  carrierCsv: File | null
  erpCsv: File | null
  etaThresholdHours: number
  uploadResult: UploadResponse | null
  setEdi850: (f: File | null) => void
  setEdi856: (f: File | null) => void
  setCarrierCsv: (f: File | null) => void
  setErpCsv: (f: File | null) => void
  setEtaThresholdHours: (n: number) => void
  setUploadResult: (r: UploadResponse | null) => void
  errors: Record<string, string | null>
  setErrors: React.Dispatch<React.SetStateAction<Record<string, string | null>>>
}

const UploadContext = createContext<UploadContextValue | null>(null)

export function UploadProvider({ children }: { children: React.ReactNode }) {
  const [edi850, setEdi850] = useState<File | null>(null)
  const [edi856, setEdi856] = useState<File | null>(null)
  const [carrierCsv, setCarrierCsv] = useState<File | null>(null)
  const [erpCsv, setErpCsv] = useState<File | null>(null)
  const [etaThresholdHours, setEtaThresholdHours] = useState<number>(48)
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null)
  const [errors, setErrors] = useState<Record<string, string | null>>({})

  return (
    <UploadContext.Provider value={{ edi850, edi856, carrierCsv, erpCsv, etaThresholdHours, uploadResult, setEdi850, setEdi856, setCarrierCsv, setErpCsv, setEtaThresholdHours, setUploadResult, errors, setErrors }}>
      {children}
    </UploadContext.Provider>
  )
}

export function useUploadContext() {
  const ctx = useContext(UploadContext)
  if (!ctx) throw new Error('useUploadContext must be used within UploadProvider')
  return ctx
}


