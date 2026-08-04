import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getCurrentUserApi, loginApi } from '../api/auth'
import { TOKEN_STORAGE_KEY } from '../api/http'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  // token 持久化到 localStorage，页面刷新后仍可调用 /me 恢复当前用户。
  const token = ref(localStorage.getItem(TOKEN_STORAGE_KEY) || '')
  const user = ref<User | null>(null)
  const restoring = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value))
  const isAdmin = computed(() => ['super_admin', 'admin'].includes(user.value?.role || ''))
  const isSuperAdmin = computed(() => user.value?.role === 'super_admin')

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
      // 不直接信任 JWT 内的角色，而是从后端获取账号的最新状态和权限。
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
    // 登录后立即校验 /me，确保后续路由守卫拥有可靠的用户和角色信息。
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
    isSuperAdmin,
    login,
    logout,
    fetchCurrentUser,
  }
})
