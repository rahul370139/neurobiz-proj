"use client"
import React, { useCallback, useRef, useState } from 'react'

type Props = {
  accept?: Record<string, string[]>
  onFiles: (files: File[]) => void | Promise<void>
}

export function FileDropzone({ accept, onFiles }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const onDrop = useCallback(async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    const files = Array.from(event.dataTransfer.files)
    if (files.length) await onFiles(filterAccepted(files, accept))
  }, [accept, onFiles])

  const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : []
    if (files.length) await onFiles(filterAccepted(files, accept))
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      className={`grid h-56 place-items-center rounded-xl border-2 border-dashed ${isDragging ? 'border-primary bg-blue-50' : 'border-slate-200 bg-white'}`}
    >
      <div className="text-center">
        <div className="text-sm font-medium text-slate-700">Drop files here or click to browse</div>
        <div className="mt-1 text-xs text-slate-500">CSV or EDI files</div>
        <button onClick={() => inputRef.current?.click()} className="mt-3 rounded-md border bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm hover:bg-muted">Browse Files</button>
        <input ref={inputRef} type="file" multiple onChange={onChange} className="hidden" accept={accept ? Object.values(accept).flat().join(',') : undefined} />
      </div>
    </div>
  )
}

function filterAccepted(files: File[], accept?: Record<string, string[]>) {
  if (!accept) return files
  const exts = new Set(Object.values(accept).flat())
  return files.filter(f => {
    const lower = f.name.toLowerCase()
    for (const ext of exts) {
      if (lower.endsWith(ext.toLowerCase())) return true
    }
    return false
  })
}


