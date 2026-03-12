const BASE = '/api'

export async function getStatus() {
  const res = await fetch(`${BASE}/status`)
  return res.json()
}

export async function uploadFiles(files) {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  let data
  try {
    data = await res.json()
  } catch (e) {
    // If response is not JSON, try to get text
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}: Upload failed`)
  }
  if (!res.ok) {
    throw new Error(data.detail || `HTTP ${res.status}: Upload failed`)
  }
  return data
}

/** @deprecated use uploadFiles */
export async function uploadPDF(file) {
  return uploadFiles([file])
}
