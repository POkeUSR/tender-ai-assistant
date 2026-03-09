import { ref } from 'vue'

export function useSSE() {
  const text = ref('')
  const loading = ref(false)
  const error = ref(null)

  async function stream(url, body = null) {
    loading.value = true
    error.value = null
    text.value = ''

    try {
      const options = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }
      if (body !== null) {
        options.body = JSON.stringify(body)
      }

      const response = await fetch(url, options)

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || `HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const raw = decoder.decode(value, { stream: true })
        const lines = raw.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (data === '[DONE]') break
            try {
              const parsed = JSON.parse(data)
              if (parsed.token) {
                text.value += parsed.token
              }
            } catch {
              // skip malformed lines
            }
          }
        }
      }
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function reset() {
    text.value = ''
    error.value = null
    loading.value = false
  }

  return { text, loading, error, stream, reset }
}
