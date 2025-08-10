import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

// Server-side proxy to call the Railway storage status API
export async function GET(req: Request) {
  try {
    const res = await fetch(apiUrls.storageStatus)

    let data: any = null
    try {
      data = await res.json()
    } catch {
      data = { status: 'not_available', initialized: false, message: 'Failed to parse response' }
    }

    return NextResponse.json({ ...data, success: res.ok }, { status: res.status })
  } catch (err: any) {
    return NextResponse.json(
      { 
        status: 'not_available',
        initialized: false,
        message: 'Storage status check failed',
        success: false, 
        error: String(err?.message || err) 
      },
      { status: 500 }
    )
  }
}
