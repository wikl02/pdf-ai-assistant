import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getCurrentUserApi, loginApi } from '../api/auth'
import { TOKEN_STORAGE_KEY } from '../api/http'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_STORAGE_KEY) || '')
  const user = ref<User | null>(null)
  const restoring = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value))
  const isAdmin = computed(() => user.value?.role === 'admin')

  function persistToken(value: string) {
    token.value = value
    localStorage.setItem(TOKEN_STORAGE_KEY, value)
  }

  function clearAuth() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  }

  async function fetchCurrentUser() {
    if (!token.value) throw new Error('missing token')
    restoring.value = true
    try {
      user.value = await getCurrentUserApi()
      return user.value
    } catch (error) {
      clearAuth()
      throw error
    } finally {
      restoring.value = false
    }
  }

  async function login(username: string, password: string) {
    const response = await loginApi(username, password)
    persistToken(response.access_token)
    await fetchCurrentUser()
    return user.value
  }

  function logout() {
    clearAuth()
  }

  return {
    token,
    user,
    restoring,
    isAuthenticated,
    isAdmin,
    login,
    logout,
    fetchCurrentUser,
  }
})
