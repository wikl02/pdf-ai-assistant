import http from './http'
import type { User, UserRole } from '../types'

export async function listUsersApi(): Promise<User[]> {
  const { data } = await http.get<User[]>('/api/admin/users')
  return data
}

export async function createUserApi(payload: {
  username: string
  password: string
  display_name?: string
  role: UserRole
}): Promise<User> {
  const { data } = await http.post<User>('/api/admin/users', payload)
  return data
}

export async function updateUserStatusApi(id: number, isActive: boolean): Promise<User> {
  const { data } = await http.patch<User>(`/api/admin/users/${id}/status`, {
    is_active: isActive,
  })
  return data
}

export async function updateUserRoleApi(id: number, role: UserRole): Promise<User> {
  const { data } = await http.patch<User>(`/api/admin/users/${id}/role`, { role })
  return data
}

export async function resetUserPasswordApi(id: number, password: string): Promise<void> {
  await http.post(`/api/admin/users/${id}/reset-password`, { password })
}
