import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => undefined)
    const res = await fetch(apiUrls.replayStrict, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    })

    let data: any = null
    try {
      data = await res.json()
    } catch {
      data = { message: 'Upstream returned non-JSON' }
    }

    return NextResponse.json({ ...data, success: res.ok }, { status: res.status })
  } catch (err: any) {
    return NextResponse.json({ success: false, error: String(err?.message || err) }, { status: 500 })
  }
}


