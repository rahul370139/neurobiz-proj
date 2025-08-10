import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

export async function GET(
  req: Request,
  { params }: { params: { digest: string } }
) {
  const { digest } = params
  const url = `${apiUrls.artifacts}/${encodeURIComponent(digest)}`
  try {
    const res = await fetch(url)
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


