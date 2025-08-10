"use client"
import React from 'react'
import { CheckCircle2, AlertCircle, UploadCloud } from 'lucide-react'
import { Button } from '@/components/ui/button'

type Props = {
  label: string
  exts: string[]
  onSelect: (file: File) => void | Promise<void>
  fileName?: string
  error?: string | null
}

export function FileSlot({ label, exts, onSelect, fileName, error }: Props) {
  const inputRef = React.useRef<HTMLInputElement | null>(null)
  const [dragOver, setDragOver] = React.useState(false)

  const onDrop: React.DragEventHandler<HTMLDivElement> = async (e) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    const accepted = filterExts(files, exts)
    if (accepted[0]) await onSelect(accepted[0])
  }

  const onChange: React.ChangeEventHandler<HTMLInputElement> = async (e) => {
    const f = e.target.files?.[0]
    if (f) await onSelect(f)
  }

  const stateIcon = error ? (
    <AlertCircle className="h-4 w-4 text-red-600" />
  ) : fileName ? (
    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
  ) : (
    <UploadCloud className="h-4 w-4 text-slate-400" />
  )

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      className={`flex items-center justify-between rounded-md border bg-white px-3 py-2 ${dragOver ? 'ring-2 ring-primary' : ''}`}
    >
      <div className="text-sm">
        <div className="font-medium">{label}</div>
        <div className="text-xs text-slate-500">{fileName || 'Drop here or click Upload'}</div>
        {error && <div className="text-xs text-red-600">{error}</div>}
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-500">
        {stateIcon}
        <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}>Upload</Button>
        <input ref={inputRef} type="file" accept={exts.join(',')} className="hidden" onChange={onChange} />
      </div>
    </div>
  )
}

function filterExts(files: File[], exts: string[]) {
  const lowerExts = exts.map(e => e.toLowerCase())
  return files.filter(f => lowerExts.some(ext => f.name.toLowerCase().endsWith(ext)))
}


