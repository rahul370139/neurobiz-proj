import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

// Server-side proxy to avoid browser CORS while calling the Railway API
export async function POST(req: Request) {
  try {
    const form = await req.formData()
    const upstream = apiUrls.upload
    const res = await fetch(upstream, { method: 'POST', body: form })

    let data: any = null
    try {
      data = await res.json()
    } catch {
      data = { message: 'Upstream returned non-JSON' }
    }

    return NextResponse.json({ ...data, success: res.ok }, { status: res.status })
  } catch (err: any) {
    return NextResponse.json(
      { message: 'Proxy error', files_processed: [], next_step: '', success: false, error: String(err?.message || err) },
      { status: 500 }
    )
  }
}


