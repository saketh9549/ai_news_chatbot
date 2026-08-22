const BASE = 'http://127.0.0.1:5000'

export async function sendMessage(query, sessionId = null, categoryFilter = null) {
  const body = { query }
  if (sessionId) body.session_id = sessionId
  if (categoryFilter) body.category_filter = categoryFilter

  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Chat error: ${res.status}`)
  return res.json()
}

export async function sendMessageStream({
  query,
  sessionId = null,
  categoryFilter = null,
  signal = null,
  onSession,
  onSessionCreated,
  onToken,
  onDone,
  onError,
}) {
  const body = { query }
  if (sessionId) body.session_id = sessionId
  if (categoryFilter) body.category_filter = categoryFilter

  try {
    const response = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })

    if (!response.ok) {
      throw new Error(`Server error (${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      if (signal?.aborted) {
        try {
          await reader.cancel()
        } catch {}
        break
      }

      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue
          try {
            const data = JSON.parse(jsonStr)
            if (data.type === 'session') {
              if (onSession) onSession(data.session_id)
              if (onSessionCreated) onSessionCreated(data.session_id)
            } else if (data.type === 'token' && onToken) {
              onToken(data.token)
            } else if (data.type === 'done' && onDone) {
              onDone({ citations: data.citations || [] })
            }
          } catch (err) {
            console.error('Error parsing SSE chunk:', err, jsonStr)
          }
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError' || signal?.aborted) {
      console.log('Stream aborted by user')
      if (onDone) onDone([])
      return
    }
    if (onError) onError(err)
    else throw err
  }
}

export async function getSessions() {
  const res = await fetch(`${BASE}/chat/sessions`)
  if (!res.ok) throw new Error(`Sessions error: ${res.status}`)
  return res.json()
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${BASE}/chat/${sessionId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Delete session error: ${res.status}`)
  return true
}

export async function getChatHistory(sessionId) {
  const res = await fetch(`${BASE}/chat/${sessionId}/history`)
  if (!res.ok) throw new Error(`History error: ${res.status}`)
  return res.json()
}

export async function getRecentArticles(category = null, limit = 15) {
  let url = `${BASE}/articles/recent?limit=${limit}`
  if (category && category !== 'all') {
    url += `&category=${encodeURIComponent(category)}`
  }
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Recent articles error: ${res.status}`)
  return res.json()
}

export async function getSources() {
  const res = await fetch(`${BASE}/sources`)
  if (!res.ok) throw new Error(`Sources error: ${res.status}`)
  return res.json()
}

export async function addSource(data) {
  const res = await fetch(`${BASE}/sources`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`Add source error: ${res.status}`)
  return res.json()
}

export async function deleteSource(sourceId) {
  const res = await fetch(`${BASE}/sources/${sourceId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Delete source error: ${res.status}`)
  return true
}

export async function triggerIngestion() {
  const res = await fetch(`${BASE}/ingest/run`, { method: 'POST' })
  if (!res.ok) throw new Error(`Ingest error: ${res.status}`)
  return res.json()
}

export async function getArticle(articleId) {
  const res = await fetch(`${BASE}/articles/${articleId}`)
  if (!res.ok) throw new Error(`Article error: ${res.status}`)
  return res.json()
}
