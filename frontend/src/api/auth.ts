import http from './http'
import type { LoginResponse, User } from '../types'

export async function loginApi(username: string, password: string): Promise<LoginResponse> {
  const { data } = await http.post<LoginResponse>('/api/auth/login', { username, password })
  return data
}

export async function getCurrentUserApi(): Promise<User> {
  const { data } = await http.get<User>('/api/auth/me')
  return data
}
