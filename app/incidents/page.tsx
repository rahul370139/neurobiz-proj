"use client"
import React from 'react'
import Link from 'next/link'
import { useUploadContext } from '@/lib/upload-context'

export default function IncidentsPage() {
  const { uploadResult, etaThresholdHours } = useUploadContext()

  const accessDenied = !uploadResult

  return (
    <main className="min-h-screen">
      <div className="sticky top-0 z-10 w-full border-b bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3">
          <div className="flex items-center gap-2 font-semibold"><div className="grid h-7 w-7 place-items-center rounded-md bg-slate-900 text-white">CT</div> Control Tower</div>
        </div>
      </div>

      <section className="mx-auto max-w-5xl px-6">
        <div className="mx-auto max-w-3xl py-6 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-slate-800">Incident Report</h1>
          <p className="mt-2 text-slate-600">Supply chain exceptions and mitigation steps</p>
        </div>

        {accessDenied ? (
          <div className="rounded-md border bg-white p-6 text-center">
            <div className="text-sm text-slate-600">Please complete the upload and configuration steps first.</div>
            <Link href="/" className="mt-3 inline-block rounded-md border px-4 py-2 text-slate-700 hover:bg-muted">Go to start</Link>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="rounded-lg border bg-card shadow-card">
              <div className="border-b px-6 py-4">
                <h2 className="text-lg font-semibold">Summary</h2>
              </div>
              <div className="grid grid-cols-1 gap-3 p-6 sm:grid-cols-3">
                <Summary label="Processing status" value={uploadResult?.message || 'Processed'} />
                <Summary label="Files processed" value={String(uploadResult?.files_processed?.length || 0)} />
                <Summary label="ETA threshold" value={`${etaThresholdHours} hours`} />
              </div>
              {uploadResult && (
                <div className={`px-6 pb-4 text-sm ${uploadResult.success !== false ? 'text-emerald-700' : 'text-red-700'}`}>
                  {uploadResult.success !== false ? 'Success: Files have been accepted for processing.' : 'Error: Upload failed. Please verify files and try again.'}
                </div>
              )}
            </div>

            <div className="rounded-lg border bg-card shadow-card">
              <div className="border-b px-6 py-4">
                <h2 className="text-lg font-semibold">Detected Incidents</h2>
              </div>
              <div className="p-6 space-y-4">
                {/* Dummy incidents */}
                <Incident title="Potential late delivery" detail="Carrier status shows delay beyond ETA for PO-1001 to Austin, TX." severity="High" />
                <Incident title="Address mismatch" detail="Ship-to state mismatch between EDI 850 and carrier record." severity="Medium" />
              </div>
            </div>

            <div className="rounded-lg border bg-card shadow-card">
              <div className="border-b px-6 py-4">
                <h2 className="text-lg font-semibold">Mitigation Steps</h2>
              </div>
              <div className="p-6 space-y-3 text-sm">
                <Step text="Notify customer of potential delay; propose split shipment." />
                <Step text="Expedite via 2-day service for backordered items." />
                <Step text="Confirm ship-to details with customer service; update ERP if needed." />
              </div>
            </div>

            <div className="flex items-center justify-end">
              <Link href="/" className="rounded-md border px-4 py-2 text-slate-700 hover:bg-muted">Start Over</Link>
            </div>
          </div>
        )}
      </section>
    </main>
  )
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-white p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-sm font-medium text-slate-800">{value}</div>
    </div>
  )
}

function Incident({ title, detail, severity }: { title: string; detail: string; severity: 'Low'|'Medium'|'High' }) {
  const color = severity === 'High' ? 'text-red-600' : severity === 'Medium' ? 'text-amber-600' : 'text-slate-600'
  return (
    <div className="rounded-md border bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-800">{title}</div>
        <span className={`text-xs ${color}`}>{severity}</span>
      </div>
      <div className="mt-1 text-sm text-slate-600">{detail}</div>
    </div>
  )
}

function Step({ text }: { text: string }) {
  return (
    <div className="rounded-md border bg-white p-3 text-slate-700">{text}</div>
  )
}


