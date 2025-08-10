import { apiUrls } from './config'

// API Response Types
export interface UploadResponse {
  message: string
  files_processed: string[]
  next_step: string
  success?: boolean
}

export interface AnalysisResult {
  order_id: string
  incidents_count: number
  processing_steps: number
  artifacts_generated: boolean
  com_json: any
  rca_json: any
  spans: any[]
  storage_results: {
    success: boolean
    artifacts_stored: number
    spans_stored: number
    incident_created: boolean
    order_id: string
  }
}

export interface FileInfo {
  name: string
  type: 'uploaded' | 'processed'
  size: number
}

export interface StorageStatus {
  status: 'available' | 'not_available'
  initialized: boolean
  message: string
}

export interface IncidentsResponse {
  incidents: any[]
  count: number
}

// API Service Class
export class ApiService {
  // File Upload
  static async uploadFiles(files: File[]): Promise<UploadResponse> {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    
    const response = await fetch(apiUrls.upload, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`)
    }
    
    return response.json()
  }

  // Run Analysis
  static async runAnalysis(): Promise<AnalysisResult> {
    const response = await fetch(apiUrls.analyze, {
      method: 'POST'
    })
    
    if (!response.ok) {
      throw new Error(`Analysis failed: ${response.statusText}`)
    }
    
    return response.json()
  }

  // Get Files List
  static async getFiles(): Promise<{ files: FileInfo[] }> {
    const response = await fetch(apiUrls.files)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch files: ${response.statusText}`)
    }
    
    return response.json()
  }

  // Get Storage Status
  static async getStorageStatus(): Promise<StorageStatus> {
    const response = await fetch(apiUrls.storageStatus)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch storage status: ${response.statusText}`)
    }
    
    return response.json()
  }

  // Get All Incidents
  static async getIncidents(): Promise<IncidentsResponse> {
    const response = await fetch(apiUrls.incidents)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch incidents: ${response.statusText}`)
    }
    
    return response.json()
  }

  // Get Order Summary
  static async getOrderSummary(orderId: string): Promise<any> {
    const response = await fetch(`${apiUrls.order}/${orderId}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch order summary: ${response.statusText}`)
    }
    
    return response.json()
  }

  // Health Check
  static async healthCheck(): Promise<{ status: string; service: string }> {
    const response = await fetch(apiUrls.health)
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`)
    }
    
    return response.json()
  }
}
