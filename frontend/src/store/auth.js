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
    async doAdminLogin(username, password) {
      try {
        const response = await login(username, password)
        const data = response.data
        const roles = data.role_codes || []
        if (!roles.includes('admin')) {
          return { success: false, error: '该账号不是管理员，不能登录管理后台' }
        }
        localStorage.setItem('admin_token', data.access_token)
        localStorage.setItem('admin_user', data.username)
        localStorage.setItem('admin_must_change_password', String(!!data.must_change_password))
        return { success: true, data }
      } catch (error) {
        const message = error?.detail || error?.message || '管理员登录失败，请稍后重试'
        return { success: false, error: message }
      }
    },
    logout() {
      this.userId = ''
      localStorage.removeItem('userId')
    }
  }
})
