/**
 * useAuth.js — Authentication state hook
 */
import { useState, useEffect, useCallback } from 'react'
import { authAPI } from '../api.js'

export function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // On mount: restore session if token exists
  useEffect(() => {
    const restore = async () => {
      if (!authAPI.isLoggedIn()) { setLoading(false); return }
      try {
        const me = await authAPI.me()
        setUser(me)
      } catch {
        authAPI.logout()
      } finally {
        setLoading(false)
      }
    }
    restore()
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await authAPI.login(email, password)
    setUser(data.user)
    return data
  }, [])

  const signup = useCallback(async (name, email, password, grade) => {
    const data = await authAPI.signup(name, email, password, grade)
    setUser(data.user)
    return data
  }, [])

  const logout = useCallback(() => {
    authAPI.logout()
    setUser(null)
  }, [])

  return { user, loading, login, signup, logout }
}
