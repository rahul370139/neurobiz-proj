import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

// Server-side proxy to call the Railway files API
export async function GET(req: Request) {
  try {
    const res = await fetch(apiUrls.files)

    let data: any = null
    try {
      data = await res.json()
    } catch {
      data = { files: [] }
    }

    return NextResponse.json({ ...data, success: res.ok }, { status: res.status })
  } catch (err: any) {
    return NextResponse.json(
      { 
        files: [],
        success: false, 
        error: String(err?.message || err) 
      },
      { status: 500 }
    )
  }
}
