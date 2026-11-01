const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '')
const SESSION_KEY = 'distribuflow.session'

export interface AuthSession {
  id: number
  username: string
  email: string
  role: string
  permissions?: string[]
  all_warehouses: boolean
  warehouse_ids: number[]
  token: string
  refresh_token: string
}

interface ApiEnvelope<T> {
  data: T
}

interface RefreshResponse {
  data: {
    token: string
    refresh_token: string
  }
}

let refreshInFlight: Promise<boolean> | null = null

export function readSession(): AuthSession | null {
  const stored = sessionStorage.getItem(SESSION_KEY)
  if (!stored) return null

  try {
    const session: unknown = JSON.parse(stored)
    if (
      typeof session === 'object' &&
      session !== null &&
      'token' in session &&
      'refresh_token' in session &&
      typeof session.token === 'string' &&
      typeof session.refresh_token === 'string' &&
      'id' in session &&
      typeof session.id === 'number' &&
      'username' in session &&
      typeof session.username === 'string' &&
      'email' in session &&
      typeof session.email === 'string' &&
      'role' in session &&
      typeof session.role === 'string' &&
      (!('permissions' in session) ||
        (Array.isArray(session.permissions) &&
          session.permissions.every((permission) => typeof permission === 'string'))) &&
      'all_warehouses' in session &&
      typeof session.all_warehouses === 'boolean' &&
      'warehouse_ids' in session &&
      Array.isArray(session.warehouse_ids) &&
      session.warehouse_ids.every((id) => typeof id === 'number')
    ) {
      return session as AuthSession
    }
  } catch {
    sessionStorage.removeItem(SESSION_KEY)
  }

  sessionStorage.removeItem(SESSION_KEY)
  return null
}

export function saveSession(session: AuthSession): void {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY)
}

async function refreshSession(): Promise<boolean> {
  const session = readSession()
  if (!session?.refresh_token) return false

  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    })
      .then(async (response) => {
        if (!response.ok) {
          clearSession()
          return false
        }
        const result = (await response.json()) as RefreshResponse
        saveSession({
          ...session,
          token: result.data.token,
          refresh_token: result.data.refresh_token,
        })
        return true
      })
      .catch(() => {
        clearSession()
        return false
      })
      .finally(() => {
        refreshInFlight = null
      })
  }

  return refreshInFlight
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  retryOnUnauthorized = true,
): Promise<T> {
  const session = readSession()
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (session?.token) headers.set('Authorization', `Bearer ${session.token}`)

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (response.status === 401 && retryOnUnauthorized && await refreshSession()) {
    const retryInit =
      path === '/auth/logout' && init.method === 'POST'
        ? {
            ...init,
            body: JSON.stringify({ refresh_token: readSession()?.refresh_token }),
          }
        : init
    return apiRequest<T>(path, retryInit, false)
  }

  const raw = await response.text()
  let payload: unknown = null
  if (raw) {
    try {
      payload = JSON.parse(raw) as unknown
    } catch {
      if (response.ok) throw new ApiError('Respons server bukan JSON yang valid.', response.status)
    }
  }

  if (!response.ok) {
    const message =
      typeof payload === 'object' &&
      payload !== null &&
      'error' in payload &&
      typeof payload.error === 'string'
        ? payload.error
        : `Permintaan gagal (${response.status}).`
    throw new ApiError(message, response.status)
  }

  return payload as T
}

export function getApiData<T>(path: string): Promise<ApiEnvelope<T>> {
  return apiRequest<ApiEnvelope<T>>(path)
}
