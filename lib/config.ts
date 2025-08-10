// Backend API Configuration
export const config = {
  backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL || 'https://neurobiz-proj-production.up.railway.app',
  apiEndpoints: {
    upload: '/upload',
    analyze: '/analyze',
    files: '/files',
    storageStatus: '/storage/status',
    incidents: '/storage/incidents',
    order: '/storage/order',
    health: '/health',
    // Additional FastAPI endpoints (AgentOps/Main/Backend variants)
    process: '/process',
    processFromSupabase: '/process/from-supabase',
    processByDigest: '/process/by-digest',
    artifacts: '/artifacts',
    artifactByDigest: '/artifacts', // base + '/:digest' when used
    incidentById: '/incidents', // base + '/:incident_id' when used
    replayStrict: '/replay/strict',
    downloadBundle: '/download' // base + '/:incident_id/bundle' when used
  }
}

// Helper function to build full API URLs
export const buildApiUrl = (endpoint: string) => {
  return `${config.backendUrl}${endpoint}`}


// API endpoints for the frontend
export const apiUrls = {
  upload: buildApiUrl('/upload'),
  analyze: buildApiUrl('/analyze'),
  files: buildApiUrl('/files'),
  storageStatus: buildApiUrl('/storage/status'),
  incidents: buildApiUrl('/storage/incidents'),
  order: buildApiUrl('/storage/order'),
  health: buildApiUrl('/health'),
  process: buildApiUrl('/process'),
  processFromSupabase: buildApiUrl('/process/from-supabase'),
  processByDigest: buildApiUrl('/process/by-digest'),
  artifacts: buildApiUrl('/artifacts'),
  incidentById: (id: string) => buildApiUrl(`/incidents/${encodeURIComponent(id)}`),
  replayStrict: buildApiUrl('/replay/strict'),
  downloadBundle: (id: string) => buildApiUrl(`/download/${encodeURIComponent(id)}/bundle`)
}
