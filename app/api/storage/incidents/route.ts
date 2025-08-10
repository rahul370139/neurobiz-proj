import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

// Server-side proxy to call the Railway incidents API
export async function GET(req: Request) {
  try {
    const res = await fetch(apiUrls.incidents)

    let data: any = null
    try {
      data = await res.json()
    } catch {
      data = { incidents: [], count: 0 }
    }

    return NextResponse.json({ ...data, success: res.ok }, { status: res.status })
  } catch (err: any) {
    return NextResponse.json(
      { 
        incidents: [],
        count: 0,
        success: false, 
        error: String(err?.message || err) 
      },
      { status: 500 }
    )
  }
}
