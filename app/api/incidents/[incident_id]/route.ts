import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

// Server-side proxy to call the custom cloud backend for incident details
// Upstream: https://neurobiz-proj-production-26c8.up.railway.app/incidents/:incident_id
export async function GET(
  req: Request,
  { params }: { params: { incident_id: string } }
) {
  const { incident_id } = params
  const url = apiUrls.incidentById(incident_id)

  try {
    const res = await fetch(url, { method: 'GET' })

    // Try to parse JSON, else return raw text so the UI can display it
    let isJson = true
    let body: any = null
    try {
      // clone stream so we can attempt json first
      body = await res.clone().json()
    } catch {
      isJson = false
      body = await res.text()
    }

    const payload = isJson
      ? { success: res.ok, isJson: true, data: body }
      : { success: res.ok, isJson: false, rawText: String(body ?? '') }

    return NextResponse.json(payload, { status: res.status })
  } catch (err: any) {
    return NextResponse.json(
      {
        message: 'Failed to fetch incident details',
        success: false,
        error: String(err?.message || err)
      },
      { status: 500 }
    )
  }
}


