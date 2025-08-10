import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

export async function GET(
  req: Request,
  { params }: { params: { incident_id: string } }
) {
  const { incident_id } = params
  const url = apiUrls.downloadBundle(incident_id)
  try {
    const res = await fetch(url)
    // Attempt to stream through; fall back to JSON result so UI can handle
    const arrayBuffer = await res.arrayBuffer()
    return new NextResponse(arrayBuffer as any, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('Content-Type') || 'application/octet-stream'
      }
    })
  } catch (err: any) {
    return NextResponse.json({ success: false, error: String(err?.message || err) }, { status: 500 })
  }
}


