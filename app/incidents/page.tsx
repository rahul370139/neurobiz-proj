"use client"
import React, { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { useUploadContext } from '@/lib/upload-context'
import { SpansFlowchart } from '@/components/spans-flowchart'

interface Incident {
  id: string
  title: string
  detail: string
  severity: 'Low' | 'Medium' | 'High'
  order_id?: string
  created_at?: string
  raw?: any
  lookup_id?: string
}

export default function IncidentsPage() {
  const { uploadResult, etaThresholdHours } = useUploadContext()
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [storageStatus, setStorageStatus] = useState<any>(null)
  const [detailsById, setDetailsById] = useState<Record<string, { loading: boolean; data?: any; error?: string }>>({})

  const accessDenied = !uploadResult

  useEffect(() => {
    if (uploadResult?.success) {
      fetchIncidents()
      fetchStorageStatus()
    }
  }, [uploadResult])

  const fetchIncidents = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/storage/incidents')
      if (!res.ok) throw new Error('Failed to fetch incidents')
      const data = await res.json()
      
      // Log the exact API response and each incident payload
      console.log('Incidents API response:', data)
      if (Array.isArray(data?.incidents)) {
        data.incidents.forEach((incident: any, index: number) => {
          console.log(`Incident [${index}] raw:`, incident)
        })
      }

      if (data.success && data.incidents) {
        // Transform backend incidents to frontend format
        const transformedIncidents = data.incidents.map((incident: any) => {
          const lookupId = incident.id 
            || incident.incident_id 
            || incident.incidentId 
            || incident.incident_number 
            || incident.number 
            || incident.order_id 
            || incident.orderId 
            || incident.code
          return {
          id: (incident.id || incident.incident_id || incident.incidentId || incident.incident_number || incident.number) || Math.random().toString(),
          title: incident.title || incident.summary || 'Supply Chain Exception',
          detail: incident.detail || incident.description || 'Exception detected during analysis',
          severity: incident.severity || 'Medium',
          order_id: incident.order_id,
          created_at: incident.created_at,
          raw: incident,
          lookup_id: lookupId
        }
        })
        setIncidents(transformedIncidents)
        // Kick off details fetches for incidents that have stable IDs
        // fetchIncidentDetailsFor(transformedIncidents)
      }
    } catch (err: any) {
      setError(err.message)
      // Fallback to dummy incidents if API fails
      setIncidents([
        { id: '1', title: 'Potential late delivery', detail: 'Carrier status shows delay beyond ETA for PO-1001 to Austin, TX.', severity: 'High' as const },
        { id: '2', title: 'Address mismatch', detail: 'Ship-to state mismatch between EDI 850 and carrier record.', severity: 'Medium' as const }
      ])
          } finally {
        setLoading(false)
      }
    }

  const fetchStorageStatus = async () => {
    try {
      const res = await fetch('/api/storage/status')
      if (res.ok) {
        const data = await res.json()
        setStorageStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch storage status:', err)
    }
  }

  // const fetchIncidentDetailsFor = async (list: Incident[]) => {
  //   const withIds = list.filter(i => !!(i.lookup_id || i.id))
  //   if (withIds.length === 0) return

  //   // Set loading states
  //   setDetailsById(prev => {
  //     const copy = { ...prev }
  //     withIds.forEach(i => {
  //       copy[i.id] = { loading: true }
  //     })
  //     return copy
  //   })

  //   await Promise.allSettled(
  //     withIds.map(async (i) => {
  //       try {
  //         const idForFetch = i.lookup_id || i.id
  //         if (!idForFetch) {
  //           setDetailsById(prev => ({ ...prev, [i.id]: { loading: false, error: 'No incident id available' } }))
  //           return
  //         }
  //         const res = await fetch(`/api/incidents/${encodeURIComponent(idForFetch)}`)
  //         const data = await res.json()
  //         if (!res.ok || data?.success === false) {
  //           // Capture non-JSON or error payloads too
  //           setDetailsById(prev => ({ ...prev, [i.id]: { loading: false, error: data?.error || data?.message || 'Failed to fetch incident details' } }))
  //           return
  //         }
  //         setDetailsById(prev => ({ ...prev, [i.id]: { loading: false, data } }))
  //       } catch (e: any) {
  //         setDetailsById(prev => ({ ...prev, [i.id]: { loading: false, error: e?.message || 'Failed to fetch' } }))
  //       }
  //     })
  //   )
  // }

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
              {storageStatus && (
                <div className="px-6 pb-4">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-slate-600">Storage:</span>
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      storageStatus.status === 'available' 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {storageStatus.status === 'available' ? 'Available' : 'Not Available'}
                    </span>
                    {storageStatus.message && (
                      <span className="text-xs text-slate-500">({storageStatus.message})</span>
                    )}
                  </div>
                </div>
              )}
              {uploadResult && (
                <div className={`px-6 pb-4 text-sm ${uploadResult.success !== false ? 'text-emerald-700' : 'text-red-700'}`}>
                  {uploadResult.success !== false ? 'Success: Files have been accepted for processing.' : 'Error: Upload failed. Please verify files and try again.'}
                </div>
              )}
            </div>

            {uploadResult?.analysis?.rca_json && (
              <div className="rounded-lg border bg-card shadow-card">
                <div className="border-b px-6 py-4">
                  <h2 className="text-lg font-semibold">Root Cause Analysis</h2>
                  <p className="text-sm text-slate-600 mt-1">AI-generated hypothesis and impact assessment</p>
                </div>
                <div className="p-6 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-md border bg-white p-4">
                      <div className="text-xs font-medium text-slate-500 mb-2">Hypothesis</div>
                      <div className="text-sm text-slate-800">{uploadResult.analysis.rca_json.hypothesis || 'Not available'}</div>
                    </div>
                    <div className="rounded-md border bg-white p-4">
                      <div className="text-xs font-medium text-slate-500 mb-2">Confidence Level</div>
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-medium text-slate-800">
                          {uploadResult.analysis.rca_json.confidence ? 
                            `${Math.round(uploadResult.analysis.rca_json.confidence * 100)}%` : 
                            'Not available'
                          }
                        </div>
                        {uploadResult.analysis.rca_json.confidence && (
                          <div className="flex-1 bg-slate-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full ${
                                uploadResult.analysis.rca_json.confidence >= 0.8 ? 'bg-green-500' :
                                uploadResult.analysis.rca_json.confidence >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${uploadResult.analysis.rca_json.confidence * 100}%` }}
                            ></div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="rounded-md border bg-white p-4">
                    <div className="text-xs font-medium text-slate-500 mb-2">Impact Assessment</div>
                    <div className="text-sm text-slate-800">{uploadResult.analysis.rca_json.impact || 'Not available'}</div>
                  </div>
                  
                  <div className="rounded-md border bg-white p-4">
                    <div className="text-xs font-medium text-slate-500 mb-2">Why (Reasoning)</div>
                    <div className="text-sm text-slate-800">{uploadResult.analysis.rca_json.why || 'Not available'}</div>
                  </div>
                  
                  {uploadResult.analysis.rca_json.supporting_refs && uploadResult.analysis.rca_json.supporting_refs.length > 0 && (
                    <div className="rounded-md border bg-white p-4">
                      <div className="text-xs font-medium text-slate-500 mb-2">Supporting References</div>
                      <div className="flex flex-wrap gap-2">
                        {uploadResult.analysis.rca_json.supporting_refs.map((ref: string, index: number) => (
                          <span key={index} className="inline-block px-2 py-1 bg-slate-100 text-slate-700 text-xs rounded">
                            {ref}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {uploadResult?.analysis?.spans && uploadResult.analysis.spans.length > 0 && (
              <div className="rounded-lg border bg-card shadow-card">
                <div className="border-b px-6 py-4">
                  <h2 className="text-lg font-semibold">Processing Flow</h2>
                  <p className="text-sm text-slate-600 mt-1">Interactive span execution graph - hover over nodes for details</p>
                </div>
                <div className="p-6">
                  <SpansFlowchart spans={uploadResult.analysis.spans} />
                </div>
              </div>
            )}

            {uploadResult && (
              <div className="rounded-lg border bg-card shadow-card">
                <div className="border-b px-6 py-4">
                  <h2 className="text-lg font-semibold">Analysis Response Text Details</h2>
                </div>
                <div className="p-6">
                  <div className="text-xs font-medium text-slate-500 mb-2">Complete Upload Response JSON</div>
                  <pre className="max-h-80 overflow-auto rounded bg-slate-50 p-3 text-xs leading-relaxed text-slate-700 whitespace-pre-wrap font-mono border">
                    {JSON.stringify(uploadResult, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* <div className="rounded-lg border bg-card shadow-card">
              <div className="border-b px-6 py-4">
                <h2 className="text-lg font-semibold">Detected Incidents</h2>
                {loading && <div className="text-sm text-slate-500">Loading incidents...</div>}
                {error && <div className="text-sm text-red-500">Error: {error}</div>}
              </div>
              <div className="p-6 space-y-4">
                {incidents.length > 0 ? (
                  incidents.map((incident) => (
                  <Incident 
                      key={incident.id}
                      title={incident.title} 
                      detail={incident.detail} 
                      severity={incident.severity}
                      orderId={incident.order_id}
                    createdAt={incident.created_at}
                    raw={incident.raw}
                    details={detailsById[incident.id]}
                    />
                  ))
                ) : (
                  <div className="text-center text-sm text-slate-500 py-8">
                    {loading ? 'Loading incidents...' : 'No incidents detected'}
                  </div>
                )}
              </div>
            </div> */}

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

function Incident({ 
  title, 
  detail, 
  severity, 
  orderId, 
  createdAt,
  raw,
  details
}: { 
  title: string; 
  detail: string; 
  severity: 'Low'|'Medium'|'High';
  orderId?: string;
  createdAt?: string;
  raw?: any;
  details?: { loading: boolean; data?: any; error?: string }
}) {
  const color = severity === 'High' ? 'text-red-600' : severity === 'Medium' ? 'text-amber-600' : 'text-slate-600'
  return (
    <div className="rounded-md border bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-800">{title}</div>
        <span className={`text-xs ${color}`}>{severity}</span>
      </div>
      <div className="mt-1 text-sm text-slate-600">{detail}</div>
      {(orderId || createdAt) && (
        <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
          {orderId && <span>Order: {orderId}</span>}
          {createdAt && <span>Created: {new Date(createdAt).toLocaleDateString()}</span>}
        </div>
      )}
      {raw && (
        <div className="mt-3">
          <div className="text-xs font-medium text-slate-500">Raw incident JSON</div>
          <pre className="mt-1 max-h-80 overflow-auto rounded bg-slate-50 p-3 text-xs leading-relaxed text-slate-700 whitespace-pre-wrap font-mono">
            {JSON.stringify(raw, null, 2)}
          </pre>
        </div>
      )}
      <div className="mt-3">
        <div className="text-xs font-medium text-slate-500">Incident details (from cloud backend)</div>
        <div className="mt-1 max-h-60 overflow-auto rounded border bg-slate-50 p-3 text-xs leading-relaxed text-slate-700 whitespace-pre-wrap">
          {details?.loading && <span className="text-slate-500">Loading…</span>}
          {!details?.loading && details?.error && (
            <span className="text-red-600">Error: {details.error}</span>
          )}
          {!details?.loading && !details?.error && details?.data?.isJson === false && (
            <pre className="font-mono">{String(details?.data?.rawText)}</pre>
          )}
          {!details?.loading && !details?.error && details?.data?.isJson === true && (
            <pre className="font-mono">{JSON.stringify(details?.data?.data, null, 2)}</pre>
          )}
          {!details?.loading && !details?.error && details?.data && details?.data?.isJson === undefined && (
            <pre className="font-mono">{JSON.stringify(details.data, null, 2)}</pre>
          )}
          {!details?.loading && !details?.error && !details?.data && (
            <span className="text-slate-500">No data found for this incident.</span>
          )}
        </div>
      </div>
    </div>
  )
}

function Step({ text }: { text: string }) {
  return (
    <div className="rounded-md border bg-white p-3 text-slate-700">{text}</div>
  )
}


