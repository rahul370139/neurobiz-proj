import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

// Server-side proxy to call the Railway analyze API
export async function POST(req: Request) {
  try {
    const res = await fetch(apiUrls.analyze, { 
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    let data: any = null
    try {
      data = await res.json()
    } catch {
      data = { message: 'Upstream returned non-JSON' }
    }

    return NextResponse.json({ ...data, success: res.ok }, { status: res.status })
  } catch (err: any) {
    return NextResponse.json(
      { 
        message: 'Analysis failed', 
        order_id: '',
        incidents_count: 0,
        processing_steps: 0,
        artifacts_generated: false,
        com_json: {},
        rca_json: {},
        spans: [],
        storage_results: {
          success: false,
          artifacts_stored: 0,
          spans_stored: 0,
          incident_created: false,
          order_id: ''
        },
        success: false, 
        error: String(err?.message || err) 
      },
      { status: 500 }
    )
  }
}
