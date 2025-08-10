"use client"
import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { FileText, Database, Activity, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

interface FileInfo {
  name: string
  type: 'uploaded' | 'processed'
  size: number
}

interface StorageStatus {
  status: 'available' | 'not_available'
  initialized: boolean
  message: string
}

interface SystemHealth {
  status: 'healthy' | 'unhealthy'
  service: string
}

export default function DashboardPage() {
  const [files, setFiles] = useState<FileInfo[]>([])
  const [storageStatus, setStorageStatus] = useState<StorageStatus | null>(null)
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      
      // Fetch files
      const filesRes = await fetch('/api/files')
      const filesData = await filesRes.json()
      
      // Fetch storage status
      const storageRes = await fetch('/api/storage/status')
      const storageData = await storageRes.json()
      
      // Fetch system health
      const healthRes = await fetch('/api/health')
      const healthData = await healthRes.json()
      
      if (filesData.success) setFiles(filesData.files || [])
      if (storageData.success) setStorageStatus(storageData)
      if (healthData.success) setSystemHealth(healthData)
      
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const refreshData = () => {
    fetchDashboardData()
  }

  if (loading) {
    return (
      <main className="min-h-screen">
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-slate-600">Loading dashboard...</p>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen">
      <div className="sticky top-0 z-10 w-full border-b bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3">
          <div className="flex items-center gap-2 font-semibold">
            <div className="grid h-7 w-7 place-items-center rounded-md bg-slate-900 text-white">CT</div> 
            Control Tower Dashboard
          </div>
          <div className="ml-auto flex items-center gap-3">
            <button 
              onClick={refreshData}
              className="rounded-md border px-3 py-1.5 text-sm text-slate-700 hover:bg-muted"
            >
              Refresh
            </button>
            <Link href="/" className="rounded-md border px-3 py-1.5 text-sm text-slate-700 hover:bg-muted">
              Upload Files
            </Link>
          </div>
        </div>
      </div>

      <section className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-slate-800">System Dashboard</h1>
          <p className="mt-2 text-slate-600">Monitor your supply chain analysis system status</p>
        </div>

        {error && (
          <div className="mb-6 rounded-md border border-red-200 bg-red-50 p-4">
            <div className="flex items-center gap-2 text-red-800">
              <XCircle className="h-5 w-5" />
              <span className="font-medium">Error:</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* System Health */}
          <div className="rounded-lg border bg-card shadow-card">
            <div className="border-b px-6 py-4">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Activity className="h-5 w-5" />
                System Health
              </h2>
            </div>
            <div className="p-6">
              {systemHealth ? (
                <div className="flex items-center gap-3">
                  {systemHealth.status === 'healthy' ? (
                    <CheckCircle className="h-6 w-6 text-green-600" />
                  ) : (
                    <XCircle className="h-6 w-6 text-red-600" />
                  )}
                  <div>
                    <div className="font-medium">
                      {systemHealth.status === 'healthy' ? 'System Healthy' : 'System Issues Detected'}
                    </div>
                    <div className="text-sm text-slate-600">{systemHealth.service}</div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-slate-500">Unable to fetch system health</div>
              )}
            </div>
          </div>

          {/* Storage Status */}
          <div className="rounded-lg border bg-card shadow-card">
            <div className="border-b px-6 py-4">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Database className="h-5 w-5" />
                Storage Status
              </h2>
            </div>
            <div className="p-6">
              {storageStatus ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    {storageStatus.status === 'available' ? (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                    <span className="font-medium">
                      {storageStatus.status === 'available' ? 'Available' : 'Not Available'}
                    </span>
                  </div>
                  <div className="text-sm text-slate-600">
                    Initialized: {storageStatus.initialized ? 'Yes' : 'No'}
                  </div>
                  {storageStatus.message && (
                    <div className="text-sm text-slate-500">{storageStatus.message}</div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-slate-500">Unable to fetch storage status</div>
              )}
            </div>
          </div>

          {/* Files Overview */}
          <div className="rounded-lg border bg-card shadow-card lg:col-span-2">
            <div className="border-b px-6 py-4">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <FileText className="h-5 w-5" />
                Files Overview
              </h2>
            </div>
            <div className="p-6">
              {files.length > 0 ? (
                <div className="space-y-3">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between rounded-md border bg-white p-3">
                      <div className="flex items-center gap-3">
                        <FileText className="h-4 w-4 text-slate-400" />
                        <div>
                          <div className="font-medium text-sm">{file.name}</div>
                          <div className="text-xs text-slate-500">
                            {file.type} • {(file.size / 1024).toFixed(1)} KB
                          </div>
                        </div>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        file.type === 'processed' 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {file.type}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <FileText className="h-12 w-12 mx-auto text-slate-300 mb-3" />
                  <p>No files uploaded yet</p>
                  <Link href="/" className="mt-2 inline-block text-primary hover:underline">
                    Upload your first files
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 rounded-lg border bg-card shadow-card">
          <div className="border-b px-6 py-4">
            <h2 className="text-lg font-semibold">Quick Actions</h2>
          </div>
          <div className="p-6">
            <div className="flex flex-wrap gap-3">
              <Link 
                href="/" 
                className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-white hover:opacity-90"
              >
                <FileText className="h-4 w-4" />
                Upload New Files
              </Link>
              <Link 
                href="/incidents" 
                className="flex items-center gap-2 rounded-md border px-4 py-2 text-slate-700 hover:bg-muted"
              >
                <AlertTriangle className="h-4 w-4" />
                View Incidents
              </Link>
              <button 
                onClick={refreshData}
                className="flex items-center gap-2 rounded-md border px-4 py-2 text-slate-700 hover:bg-muted"
              >
                <Activity className="h-4 w-4" />
                Refresh Data
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
