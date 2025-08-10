"use client"
import Link from 'next/link'
import { FileUp, UploadCloud, CheckCircle2, AlertCircle, Zap, Brain } from 'lucide-react'
import React from 'react'
import { useUploadContext } from '@/lib/upload-context'
import { FileDropzone } from '@/components/file-dropzone'
import { FileSlot } from '@/components/file-slot'
import { validateEdi850, validateEdi856 } from '@/lib/validators'
import { Stepper as StepperComp } from '@/components/stepper'

export default function Page1() {
  const { edi850, edi856, setEdi850, setEdi856, setErrors, errors } = useUploadContext()

  const handleFiles = async (files: File[]) => {
    const newErrors: Record<string, string | null> = {}
    for (const f of files) {
      const text = await f.text()
      const is850 = validateEdi850(text).valid
      const is856 = validateEdi856(text).valid

      if (is850 && !is856) {
        setEdi850(f)
        newErrors.edi850 = null
        continue
      }
      if (is856 && !is850) {
        setEdi856(f)
        newErrors.edi856 = null
        continue
      }
      // If neither clearly validates, avoid assigning to the wrong slot.
      if (/850/i.test(f.name)) {
        newErrors.edi850 = 'This is not an 850 transaction set'
        continue
      }
      if (/856/i.test(f.name)) {
        newErrors.edi856 = 'This is not an 856 transaction set'
        continue
      }
    }
    setErrors(prev => ({ ...prev, ...newErrors }))
  }

  const ready = !!edi850 && !!edi856 && !errors.edi850 && !errors.edi856

  return (
    <main className="min-h-screen">
      <TopNav />
      <section className="mx-auto max-w-5xl px-6">
        <Header />
        <Stepper current={0} />

        <div className="mt-6 rounded-lg border bg-card shadow-card">
          <div className="border-b px-6 py-4">
            <h2 className="flex items-center gap-2 text-lg font-semibold"><FileUp className="h-5 w-5"/> EDI Documents</h2>
            <p className="mt-1 text-sm text-slate-600">Drop your EDI 850 (Purchase Order) and EDI 856 (Advance Ship Notice)</p>
          </div>
          <div className="p-6">
            <FileDropzone accept={{ 'text/plain': ['.edi', '.x12', '.txt'] }} onFiles={handleFiles} />

            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <FileSlot
                label="EDI 850 (Purchase Order)"
                exts={[".edi", ".x12", ".txt"]}
                fileName={edi850?.name}
                error={errors.edi850}
                onSelect={async (file) => {
                  setEdi850(file)
                  const text = await file.text()
                  const r = validateEdi850(text)
                  setErrors(prev => ({ ...prev, edi850: r.valid ? null : r.message }))
                }}
              />

              <FileSlot
                label="EDI 856 (Advance Ship Notice)"
                exts={[".edi", ".x12", ".txt"]}
                fileName={edi856?.name}
                error={errors.edi856}
                onSelect={async (file) => {
                  setEdi856(file)
                  const text = await file.text()
                  const r = validateEdi856(text)
                  setErrors(prev => ({ ...prev, edi856: r.valid ? null : r.message }))
                }}
              />
            </div>

            <div className="mt-8 flex items-center justify-between">
              <button className="rounded-md border px-4 py-2 text-slate-600 hover:bg-muted">Previous</button>
              <Link href={ready ? '/page-2' : '#'} onClick={(e) => { if (!ready) e.preventDefault() }} className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-white ${ready ? 'bg-primary hover:opacity-95' : 'bg-slate-300 cursor-not-allowed'}`} aria-disabled={!ready}>Next</Link>
            </div>

            <div className="mt-8 text-xs text-slate-600">
              EDI files typically have `.edi` or `.x12` extensions and contain ISA/GS control segments and ST/SE transaction sets.
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

function TopNav() {
  return (
    <div className="sticky top-0 z-10 w-full border-b bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3">
        <div className="flex items-center gap-2 font-semibold"><div className="grid h-7 w-7 place-items-center rounded-md bg-slate-900 text-white">CT</div> Control Tower</div>
        <div className="ml-auto flex items-center gap-3 text-xs text-slate-500">
          <Link href="/dashboard" className="rounded-md bg-muted px-2 py-1 shadow-sm hover:bg-slate-200">Dashboard</Link>
          <span className="rounded-md bg-muted px-2 py-1 shadow-sm">Load Sample Data</span>
        </div>
      </div>
    </div>
  )
}

function Header() {
  return (
    <div className="mx-auto max-w-3xl py-6 text-center">
      <h1 className="text-4xl font-bold tracking-tight text-slate-800">Supply Chain Analysis</h1>
      <p className="mt-2 text-slate-600">Upload your supply chain documents for AI-powered exception detection</p>
      <div className="mt-3 flex items-center justify-center gap-6 text-xs text-slate-500">
        <div className="flex items-center gap-1"><Zap className="h-3 w-3 text-primary"/> Real-time Detection</div>
        <div className="flex items-center gap-1"><Brain className="h-3 w-3 text-emerald-500"/> AI-Powered Analysis</div>
      </div>
    </div>
  )
}

function Stepper({ current }: { current: 0 | 1 | 2 }) { return <StepperComp current={current} /> }

function RequiredItem({ label, file, error }: { label: string, file?: string, error?: string | null }) {
  const stateIcon = error ? <AlertCircle className="h-4 w-4 text-red-600"/> : file ? <CheckCircle2 className="h-4 w-4 text-emerald-600"/> : <UploadCloud className="h-4 w-4 text-slate-400"/>
  const stateText = error ? 'Invalid' : file ? 'Ready' : 'Required'
  return (
    <div className="flex items-center justify-between rounded-md border bg-white px-3 py-2">
      <div className="text-sm">
        <div className="font-medium">{label}</div>
        <div className="text-xs text-slate-500">{file || 'No file selected'}</div>
        {error && <div className="text-xs text-red-600">{error}</div>}
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-500">
        {stateIcon}
        <span>{stateText}</span>
      </div>
    </div>
  )
}


