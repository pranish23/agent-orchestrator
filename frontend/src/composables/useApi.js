/**
 * API composable for making requests to the FastAPI backend
 */
import { ref } from 'vue'

const API_BASE = '/api/v1'

export function useApi() {
  const loading = ref(false)
  const error = ref(null)

  async function fetchJson(url, options = {}) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}${url}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }
      
      return await response.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // Query endpoint
  async function submitQuery(query, conversationId = null) {
    return fetchJson('/query', {
      method: 'POST',
      body: JSON.stringify({
        query,
        conversation_id: conversationId,
      }),
    })
  }

  // Data endpoints
  async function getGmailData(limit = 50) {
    return fetchJson(`/data/gmail?limit=${limit}`)
  }

  async function getGcalData(limit = 50) {
    return fetchJson(`/data/gcal?limit=${limit}`)
  }

  async function getGdriveData(limit = 50) {
    return fetchJson(`/data/gdrive?limit=${limit}`)
  }

  // Health check
  async function healthCheck() {
    const response = await fetch('/health')
    return response.json()
  }

  return {
    loading,
    error,
    submitQuery,
    getGmailData,
    getGcalData,
    getGdriveData,
    healthCheck,
  }
}
