const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE ||
  'http://127.0.0.1:8000'
).replace(/\/$/, '')

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail || `Request failed with ${response.status}`)
  }

  return response.json()
}

export function getHealth() {
  return request('/health')
}

export function createReviewTask(payload) {
  return request('/api/review-tasks', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getReviewTask(taskId) {
  return request(`/api/review-tasks/${taskId}`)
}

export function listReviewTasks() {
  return request('/api/review-tasks')
}
