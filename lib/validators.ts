import Papa from 'papaparse'

export type ValidationResult = { valid: boolean; message?: string }

// Very lightweight heuristics for EDI 850 and 856 (X12). Real-world parsers are complex.
export function validateEdi850(text: string): ValidationResult {
  // Must include ISA, GS, ST*850, and SE/GE/IEA control segments
  if (!/\bISA\b/.test(text)) return { valid: false, message: 'Missing ISA segment' }
  if (!/\bGS\b/.test(text)) return { valid: false, message: 'Missing GS segment' }
  if (!/\bST\*?850\b/.test(text)) return { valid: false, message: 'This is not an 850 transaction set' }
  if (!/\bSE\b/.test(text) || !/\bGE\b/.test(text) || !/\bIEA\b/.test(text)) {
    return { valid: false, message: 'Missing control trailer segments (SE/GE/IEA)' }
  }
  return { valid: true }
}

export function validateEdi856(text: string): ValidationResult {
  if (!/\bISA\b/.test(text)) return { valid: false, message: 'Missing ISA segment' }
  if (!/\bGS\b/.test(text)) return { valid: false, message: 'Missing GS segment' }
  if (!/\bST\*?856\b/.test(text)) return { valid: false, message: 'This is not an 856 transaction set' }
  if (!/\bSE\b/.test(text) || !/\bGE\b/.test(text) || !/\bIEA\b/.test(text)) {
    return { valid: false, message: 'Missing control trailer segments (SE/GE/IEA)' }
  }
  return { valid: true }
}

// CSV validators
export const CARRIER_REQUIRED_COLUMNS = [
  'tracking_number',
  'carrier',
  'service',
  'po_number',
  'shipment_id',
  'last_update',
  'eta',
  'status',
  'location',
  'notes'
]

export async function validateCarrierCsv(csv: string): Promise<ValidationResult> {
  return validateCsvHasColumns(csv, CARRIER_REQUIRED_COLUMNS, 'Carrier')
}

export const ERP_REQUIRED_COLUMNS = [
  'po_number','po_date','customer_code','customer_name','ship_to_code','ship_to_name','ship_to_city','ship_to_state',
  'sku','qty_ordered','unit_price','promise_date','status'
]

export async function validateErpCsv(csv: string): Promise<ValidationResult> {
  return validateCsvHasColumns(csv, ERP_REQUIRED_COLUMNS, 'ERP')
}

async function validateCsvHasColumns(csv: string, requiredColumns: string[], label: string): Promise<ValidationResult> {
  const parsed = Papa.parse(csv, { header: true, skipEmptyLines: true })
  if (parsed.errors?.length) {
    return { valid: false, message: `${label} CSV parse error: ${parsed.errors[0].message}` }
  }
  const headers = (parsed.meta.fields || []).map(h => normalize(h))
  const missing = requiredColumns.filter(c => !headers.includes(normalize(c)))
  if (missing.length) return { valid: false, message: `${label} CSV missing columns: ${missing.join(', ')}` }
  return { valid: true }
}

function normalize(s: string) {
  return s.trim().toLowerCase().replace(/\s+/g, '_')
}


