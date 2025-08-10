import React from 'react'

export function Stepper({ current }: { current: 0 | 1 | 2 }) {
  const steps: Array<{ label: string }> = [
    { label: 'EDI Documents' },
    { label: 'CSV Data' },
    { label: 'Configuration' },
  ]
  return (
    <div className="mx-auto mb-4 flex max-w-3xl items-center justify-center gap-6">
      {steps.map((s, idx) => (
        <React.Fragment key={s.label}>
          <div className={`flex items-center gap-2 ${current === idx ? 'text-slate-900' : 'text-slate-400'}`}>
            <div className={`grid h-7 w-7 place-items-center rounded-full border ${current===idx? 'border-primary text-primary' : ''}`}>
              {idx+1}
            </div>
            <span className="text-sm font-medium">{s.label}</span>
          </div>
          {idx !== steps.length-1 && <div className="h-px w-16 bg-slate-200"/>}
        </React.Fragment>
      ))}
    </div>
  )
}


