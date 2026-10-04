import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export interface User {
  id: number
  username: string
  role: string
  phone?: string | null
  email?: string | null
  membership_tier?: string
  membership_points?: number
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)

  async function fetchUser() {
    try {
      const { data } = await api.get<User>('/auth/me')
      user.value = data
    } catch {
      user.value = null
    }
  }

  async function updateProfile(phone?: string | null, email?: string | null) {
    const { data } = await api.put<User>('/auth/me', { phone, email })
    user.value = data
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      await api.post('/auth/login', { username, password })
      await fetchUser()
    } finally {
      loading.value = false
    }
  }

  async function register(username: string, password: string) {
    loading.value = true
    try {
      await api.post('/auth/register', { username, password })
      await login(username, password)
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    await api.post('/auth/logout')
    user.value = null
  }

  return { user, loading, fetchUser, updateProfile, login, register, logout }
})
