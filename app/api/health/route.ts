import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

// Server-side proxy to call the Railway health check API
export async function GET(req: Request) {
  try {
    const res = await fetch(apiUrls.health)

    let data: any = null
    try {
      data = await res.json()
    } catch {
      data = { status: 'unhealthy', service: 'Unknown' }
    }

    return NextResponse.json({ ...data, success: res.ok }, { status: res.status })
  } catch (err: any) {
    return NextResponse.json(
      { 
        status: 'unhealthy',
        service: 'Frontend Proxy',
        success: false, 
        error: String(err?.message || err) 
      },
      { status: 500 }
    )
  }
}
