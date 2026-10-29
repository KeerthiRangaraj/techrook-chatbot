
/**
 * api.js — Centralised API service layer
 * Authentication, persistent chat history, and checklist.
 */

const BASE = import.meta.env.VITE_API_URL || '/api'

const getToken = () => localStorage.getItem('tr_token')

const headers = (extra = {}) => ({
  'Content-Type': 'application/json',
  ...(getToken()
    ? { Authorization: `Bearer ${getToken()}` }
    : {}),
  ...extra,
})

const handleResponse = async (res) => {
  const data = await res.json()

  if (!res.ok) {
    throw new Error(data.detail || 'Request failed')
  }

  return data
}

// ── Authentication ───────────────────────────────────────────────────────────

export const authAPI = {
  async login(email, password) {
    const res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ email, password }),
    })

    const data = await handleResponse(res)
    localStorage.setItem('tr_token', data.token)
    return data
  },

  async signup(name, email, password, grade) {
    const res = await fetch(`${BASE}/auth/signup`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ name, email, password, grade }),
    })

    const data = await handleResponse(res)
    localStorage.setItem('tr_token', data.token)
    return data
  },

  async me() {
    const res = await fetch(`${BASE}/auth/me`, {
      headers: headers(),
    })

    return handleResponse(res)
  },

  logout() {
    localStorage.removeItem('tr_token')
  },

  isLoggedIn() {
    return !!getToken()
  },
}

// ── Conversations ────────────────────────────────────────────────────────────

export const conversationAPI = {

  // Create a new conversation
  async create(title = 'New Chat') {
    const res = await fetch(`${BASE}/conversations`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ title }),
    })

    return handleResponse(res)
  },

  // Retrieve all conversations for the logged-in user
  async list() {
    const res = await fetch(`${BASE}/conversations`, {
      headers: headers(),
    })

    return handleResponse(res)
  },

  // Retrieve messages from a selected conversation
  async getMessages(conversationId) {
    const res = await fetch(
      `${BASE}/conversations/${encodeURIComponent(conversationId)}/messages`,
      {
        headers: headers(),
      }
    )

    return handleResponse(res)
  },
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export const chatAPI = {

  async send(message, conversationId = null) {
    const res = await fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    })

    return handleResponse(res)
  },

}

// ── Checklist ────────────────────────────────────────────────────────────────

export const checklistAPI = {

  async get() {
    const res = await fetch(`${BASE}/checklist`, {
      headers: headers(),
    })

    return handleResponse(res)
  },

  async update(item_id, completed) {
    const res = await fetch(`${BASE}/checklist`, {
      method: 'PUT',
      headers: headers(),
      body: JSON.stringify({
        item_id,
        completed,
      }),
    })

    return handleResponse(res)
  },

}
