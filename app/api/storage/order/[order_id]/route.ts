import { NextResponse } from 'next/server'
import { apiUrls } from '@/lib/config'

// Server-side proxy to call the Railway order summary API
export async function GET(
  req: Request,
  { params }: { params: { order_id: string } }
) {
  try {
    const orderId = params.order_id
    const res = await fetch(`${apiUrls.order}/${orderId}`)

    let data: any = null
    try {
      data = await res.json()
    } catch {
      data = { message: 'Failed to parse order data' }
    }

    return NextResponse.json({ ...data, success: res.ok }, { status: res.status })
  } catch (err: any) {
    return NextResponse.json(
      { 
        message: 'Failed to fetch order summary',
        success: false, 
        error: String(err?.message || err) 
      },
      { status: 500 }
    )
  }
}
