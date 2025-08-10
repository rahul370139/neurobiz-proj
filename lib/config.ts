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
    health: '/health'
  }
}

// Helper function to build full API URLs
export const buildApiUrl = (endpoint: string) => {
  return `${config.backendUrl}${endpoint}`
}

// API endpoints for the frontend
export const apiUrls = {
  upload: buildApiUrl('/upload'),
  analyze: buildApiUrl('/analyze'),
  files: buildApiUrl('/files'),
  storageStatus: buildApiUrl('/storage/status'),
  incidents: buildApiUrl('/storage/incidents'),
  order: buildApiUrl('/storage/order'),
  health: buildApiUrl('/health')
}
