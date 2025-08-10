"use client"
import Link from 'next/link'
import React from 'react'
import { useUploadContext } from '@/lib/upload-context'
import { FileDropzone } from '@/components/file-dropzone'
import { FileSlot } from '@/components/file-slot'
import { validateCarrierCsv, validateErpCsv, CARRIER_REQUIRED_COLUMNS, ERP_REQUIRED_COLUMNS } from '@/lib/validators'
import { CheckCircle2, AlertCircle, Zap, Brain } from 'lucide-react'
import { Stepper as StepperComp } from '@/components/stepper'

export default function Page2() {
  const { carrierCsv, erpCsv, setCarrierCsv, setErpCsv, errors, setErrors } = useUploadContext()

  const handleFiles = async (files: File[]) => {
    const newErrors: Record<string, string | null> = {}
    for (const f of files) {
      const text = await f.text()
      const isCarrier = (await validateCarrierCsv(text)).valid
      const isErp = (await validateErpCsv(text)).valid

      if (isCarrier && !isErp) {
        setCarrierCsv(f)
        newErrors.carrier = null
        continue
      }
      if (isErp && !isCarrier) {
        setErpCsv(f)
        newErrors.erp = null
        continue
      }
      if (/carrier/i.test(f.name)) {
        newErrors.carrier = 'Carrier CSV missing required columns'
        continue
      }
      if (/erp/i.test(f.name)) {
        newErrors.erp = 'ERP CSV missing required columns'
        continue
      }
    }
    setErrors(prev => ({ ...prev, ...newErrors }))
  }

  const ready = !!carrierCsv && !!erpCsv && !errors.carrier && !errors.erp

  return (
    <main className="min-h-screen">
      <div className="sticky top-0 z-10 w-full border-b bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3">
          <div className="flex items-center gap-2 font-semibold"><div className="grid h-7 w-7 place-items-center rounded-md bg-slate-900 text-white">CT</div> Control Tower</div>
        </div>
      </div>

      <section className="mx-auto max-w-5xl px-6">
        <div className="mx-auto max-w-3xl py-6 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-slate-800">Supply Chain Analysis</h1>
          <p className="mt-2 text-slate-600">Upload your ERP export and carrier tracking data</p>
          <div className="mt-3 flex items-center justify-center gap-6 text-xs text-slate-500">
            <div className="flex items-center gap-1"><Zap className="h-3 w-3 text-primary"/> Real-time Detection</div>
            <div className="flex items-center gap-1"><Brain className="h-3 w-3 text-emerald-500"/> AI-Powered Analysis</div>
          </div>
        </div>
        <StepperComp current={1} />

        <div className="mt-6 rounded-lg border bg-card shadow-card">
          <div className="border-b px-6 py-4">
            <h2 className="text-lg font-semibold">CSV Data</h2>
            <p className="mt-1 text-sm text-slate-600">Upload your ERP export and carrier tracking data</p>
          </div>
          <div className="p-6">
            <FileDropzone accept={{ 'text/csv': ['.csv'] }} onFiles={handleFiles} />

            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <FileSlot
                label="ERP Export"
                exts={[".csv"]}
                fileName={erpCsv?.name}
                error={errors.erp}
                onSelect={async (file) => {
                  setErpCsv(file)
                  const text = await file.text()
                  const r = await validateErpCsv(text)
                  setErrors(prev => ({ ...prev, erp: r.valid ? null : r.message }))
                }}
              />
              <FileSlot
                label="Carrier Tracking"
                exts={[".csv"]}
                fileName={carrierCsv?.name}
                error={errors.carrier}
                onSelect={async (file) => {
                  setCarrierCsv(file)
                  const text = await file.text()
                  const r = await validateCarrierCsv(text)
                  setErrors(prev => ({ ...prev, carrier: r.valid ? null : r.message }))
                }}
              />
            </div>

            <div className="mt-8 flex items-center justify-between">
              <Link href="/" className="rounded-md border px-4 py-2 text-slate-600 hover:bg-muted">Previous</Link>
              <Link href={ready ? '/configuration' : '#'} onClick={(e) => { if (!ready) e.preventDefault() }} className={`rounded-md px-4 py-2 text-white ${ready ? 'bg-primary hover:opacity-95' : 'bg-slate-300 cursor-not-allowed'}`}>Next</Link>
            </div>

            <div className="mt-8">
              <h3 className="text-sm font-medium text-slate-700">Expected ERP columns:</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {ERP_REQUIRED_COLUMNS.map((c) => (
                  <span key={c} className="rounded-full border bg-white px-2 py-0.5 text-xs text-slate-600 shadow-sm">{c}</span>
                ))}
              </div>
              <h3 className="mt-4 text-sm font-medium text-slate-700">Expected Carrier columns:</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {CARRIER_REQUIRED_COLUMNS.map((c) => (
                  <span key={c} className="rounded-full border bg-white px-2 py-0.5 text-xs text-slate-600 shadow-sm">{c}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

function Item({ label, file, error }: { label: string, file?: string, error?: string | null }) {
  const ok = !!file && !error
  return (
    <div className="flex items-center justify-between rounded-md border bg-white px-3 py-2">
      <div className="text-sm">
        <div className="font-medium">{label}</div>
        <div className="text-xs text-slate-500">{file || 'No file selected'}</div>
        {error && <div className="text-xs text-red-600">{error}</div>}
      </div>
      {ok ? <CheckCircle2 className="h-4 w-4 text-emerald-600"/> : error ? <AlertCircle className="h-4 w-4 text-red-600"/> : null}
    </div>
  )
}


