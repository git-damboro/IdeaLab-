import { defineStore } from 'pinia'
import { login, register } from '../services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    userId: localStorage.getItem('userId') || ''
  }),
  actions: {
    async doLogin(username, password) {
      try {
        const response = await login(username, password)
        this.userId = username
        localStorage.setItem('userId', username)
        return { success: true, data: response.data }
      } catch (error) {
        const message = error?.detail || error?.message || '登录失败，请检查用户名和密码'
        return { success: false, error: message }
      }
    },
    async doRegister(username, password) {
      try {
        const response = await register(username, password)
        return { success: true, data: response.data }
      } catch (error) {
        const message = error?.detail || error?.message || '注册失败，请稍后重试'
        return { success: false, error: message }
      }
    },
    logout() {
      this.userId = ''
      localStorage.removeItem('userId')
    }
  }
})





