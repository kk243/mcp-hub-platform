const BASE = (import.meta.env.VITE_API_BASE || '/api') + '/hub'

async function request(path, options) {
  const res = await fetch(BASE + path, options)
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail
    throw new Error(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : res.statusText)
  }
  return body
}

function get(path, params = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
  return request(qs ? `${path}?${qs}` : path)
}

function post(path, data) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

const enc = encodeURIComponent

export const getMe = () => get('/me')
export const getWorkflows = (params) => get('/workflows', params)
export const getWorkflow = (key) => get(`/workflows/${enc(key)}`)
export const getItems = (params) => get('/items', params)
export const getItem = (key) => get(`/items/${enc(key)}`)
export const getItemCode = (key) => get(`/items/${enc(key)}/code`)

export function importZip(file, dryRun) {
  const form = new FormData()
  form.append('file', file)
  return request(`/admin/import?dry_run=${dryRun ? 1 : 0}`, { method: 'POST', body: form })
}

export const updateMeta = (target, key, fields) => post('/admin/update', { target, key, fields })
export const deprecate = (target, key, replaced_by) => post('/admin/deprecate', { target, key, replaced_by })
export const setVisibility = (key, code_visibility, allowlist) =>
  post('/admin/visibility', { key, code_visibility, allowlist })
