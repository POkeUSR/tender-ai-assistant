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
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Upload failed')
  }
  return res.json()
}

/** @deprecated use uploadFiles */
export async function uploadPDF(file) {
  return uploadFiles([file])
}
