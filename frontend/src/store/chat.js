import { defineStore } from 'pinia'
import { chat } from '../services/api'

export const useChatStore = defineStore('chat', {
  state: () => ({
    history: []
  }),
  actions: {
    async ask(prompt, context) {
      this.history.push({ role: 'user', content: prompt })
      try {
        const { data } = await chat(prompt, (context || []).slice(0, 5))
        this.history.push({ role: 'assistant', content: data?.response || '抱歉，暂时无法获取回答。' })
      } catch (error) {
        console.error('Chat error:', error)
        this.history.push({ role: 'assistant', content: '抱歉，暂时无法获取回答。请稍后重试。' })
        throw error
      }
    },
    reset() {
      this.history = []
    }
  }
})





