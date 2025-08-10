"use client"
import React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Stepper as StepperComp } from '@/components/stepper'
import { useUploadContext } from '@/lib/upload-context'
import { UploadResponse } from '@/lib/api'

export default function ConfigurationPage() {
  const { edi850, edi856, carrierCsv, erpCsv, etaThresholdHours, setEtaThresholdHours } = useUploadContext()

  const totalFiles = [edi850, edi856, carrierCsv, erpCsv].filter(Boolean).length

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
          <p className="mt-2 text-slate-600">Adjust detection threshold and confirm configuration</p>
        </div>

        <StepperComp current={2} />

        <div className="mt-6 rounded-lg border bg-card shadow-card">
          <div className="border-b px-6 py-4">
            <h2 className="text-lg font-semibold">Configuration</h2>
          </div>
          <div className="p-6 space-y-8">
            <div>
              <div className="mb-2 text-sm font-medium text-slate-700">ETA threshold (hours)</div>
              <input type="range" min={4} max={168} step={4} value={etaThresholdHours} onChange={(e) => setEtaThresholdHours(Number(e.target.value))} className="w-full" />
              <div className="mt-2 text-sm text-slate-600">Current: <span className="font-medium">{etaThresholdHours}h</span></div>
            </div>

            <div className="rounded-md border bg-white p-4">
              <div className="text-sm font-semibold text-slate-800">Analysis Summary</div>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <SummaryItem label="Total files uploaded" value={String(totalFiles)} />
                <SummaryItem label="Detection threshold" value={`${etaThresholdHours} hours`} />
                <SummaryItem label="Processing mode" value="Deterministic" />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <Link href="/page-2" className="rounded-md border px-4 py-2 text-slate-600 hover:bg-muted">Previous</Link>
              <SubmitButton />
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

function SummaryItem({ label, value }: { label: string, value: string }) {
  return (
    <div className="rounded-md border bg-white p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-sm font-medium text-slate-800">{value}</div>
    </div>
  )
}

function SubmitButton() {
  const { edi850, edi856, carrierCsv, erpCsv, etaThresholdHours, setUploadResult } = useUploadContext()
  const [loading, setLoading] = React.useState(false)
  const [result, setResult] = React.useState<UploadResponse | null>(null)
  const ready = [edi850, edi856, carrierCsv, erpCsv].every(Boolean)
  const router = useRouter()

  const onSubmit = async () => {
    if (!ready) return
    setLoading(true)
    try {
      // Step 1: Upload files
      const form = new FormData()
      if (edi850) form.append('files', edi850, edi850.name)
      if (edi856) form.append('files', edi856, edi856.name)
      if (carrierCsv) form.append('files', carrierCsv, carrierCsv.name)
      if (erpCsv) form.append('files', erpCsv, erpCsv.name)
      form.append('eta_threshold_hours', String(etaThresholdHours))

      const uploadRes = await fetch('/api/upload', { method: 'POST', body: form })
      if (!uploadRes.ok) throw new Error('Upload failed')
      const uploadData = await uploadRes.json()
      
      // Log the upload response details
      console.log('File Upload Response:', {
        status: uploadRes.status,
        statusText: uploadRes.statusText,
        data: uploadData
      })
      
      // Step 2: Run analysis
      const analysisRes = await fetch('/api/analyze', { method: 'POST' })
      if (!analysisRes.ok) throw new Error('Analysis failed')
      const analysisData = await analysisRes.json()
      
      // Log the analysis response details
      console.log('Analysis Response:', {
        status: analysisRes.status,
        statusText: analysisRes.statusText,
        data: analysisData
      })
      
      // Combine results
      const response: UploadResponse = { 
        ...uploadData, 
        success: true,
        analysis: analysisData
      }
      setResult(response)
      setUploadResult(response)
      
      // Navigate to incidents page
      router.push('/incidents')
    } catch (e) {
      const fallback: UploadResponse = { message: 'Upload failed', files_processed: [], next_step: '', success: false }
      setResult(fallback)
      setUploadResult(fallback)
      router.push('/incidents')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button onClick={onSubmit} disabled={!ready || loading} className={`rounded-md px-4 py-2 text-white ${ready && !loading ? 'bg-primary hover:opacity-95' : 'bg-slate-300 cursor-not-allowed'}`}>{loading ? 'Uploading...' : 'Submit'}</button>
      {result && <span className="text-sm text-slate-600">{result.message}</span>}
    </div>
  )
}


