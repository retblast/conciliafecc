const API_BASE = import.meta.env.VITE_API_URL || '/api'

export const SOURCES = ['ura', 'biblioteca', 'no_adeudos']

const sourceLabels = {
  ura: 'URA',
  biblioteca: 'Biblioteca',
  no_adeudos: 'Constancia de No Adeudos',
}

export function sourceLabel(source) {
  return sourceLabels[source]
}

export class ConciliationApiError extends Error {
  constructor(status, error) {
    super(error.mensaje || 'Error de la API de conciliación')
    this.name = 'ConciliationApiError'
    this.status = status
    this.error = error
  }
}

async function parseError(response) {
  try {
    const body = await response.json()
    return body.error
  } catch {
    return { codigo: 'error_http', mensaje: `Error HTTP ${response.status}`, fuente: null }
  }
}

export async function conciliar(archivos) {
  const formData = new FormData()
  for (const source of SOURCES) {
    formData.append(source, archivos[source], archivos[source].name)
  }

  const response = await fetch(`${API_BASE}/api/v1/validaciones`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const apiError = await parseError(response)
    throw new ConciliationApiError(response.status, apiError)
  }

  return await response.json()
}

export async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) {
    throw new Error(`Error al consultar el estado del servicio: ${response.status}`)
  }
  return await response.json()
}
