import { request } from './client'

export type User = {
  id: number
  email: string
  created_at: string
}

export type Credentials = {
  email: string
  password: string
}

export const getCurrentUser = (): Promise<User> => request<User>('/api/auth/me')

export const register = (credentials: Credentials): Promise<User> =>
  request<User>('/api/auth/register', { method: 'POST', body: JSON.stringify(credentials) })

export const logIn = (credentials: Credentials): Promise<User> =>
  request<User>('/api/auth/login', { method: 'POST', body: JSON.stringify(credentials) })

/** Answers 204. The cookie is httpOnly, so clearing it is the server's job, not ours. */
export const logOut = (): Promise<void> => request<void>('/api/auth/logout', { method: 'POST' })
