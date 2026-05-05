import { defineStore } from 'pinia'
import {
  fetchFavorites,
  fetchFolders,
  addFavorite,
  removeFavorite,
  addFolder,
  deleteFolder
} from '../services/api'

export const useFavStore = defineStore('fav', {
  state: () => ({
    folders: ['默认收藏夹'],
    items: [],
    current: '默认收藏夹'
  }),
  actions: {
    async load(userId) {
      try {
        const [foldersRes, favRes] = await Promise.all([
          fetchFolders(userId),
          fetchFavorites(userId)
        ])
        const folders = foldersRes.data || []
        this.folders = folders.includes('默认收藏夹') ? folders : ['默认收藏夹', ...folders]
        this.items = favRes.data || []
      } catch (error) {
        console.error('Load favorites error:', error)
        this.folders = ['默认收藏夹']
        this.items = []
      }
    },
    async toggle(userId, paper, folder = '默认收藏夹') {
      try {
        const exists = this.items.some((p) => p.id === paper.id)
        if (exists) {
          await removeFavorite(userId, paper.id)
          this.items = this.items.filter((p) => p.id !== paper.id)
          paper.is_favorited = false
        } else {
          await addFavorite(userId, paper, folder)
          this.items.unshift({ ...paper, folder })
          paper.is_favorited = true
        }
      } catch (error) {
        console.error('Toggle favorite error:', error)
        throw error
      }
    },
    async createFolder(userId, name) {
      if (!name) return
      try {
        await addFolder(userId, name)
        this.folders.push(name)
      } catch (error) {
        console.error('Create folder error:', error)
        throw error
      }
    },
    async removeFolder(userId, name) {
      if (name === '默认收藏夹') return
      try {
        await deleteFolder(userId, name)
        this.folders = this.folders.filter((f) => f !== name)
        this.items = this.items.filter((p) => p.folder !== name)
        this.current = '默认收藏夹'
      } catch (error) {
        console.error('Remove folder error:', error)
        throw error
      }
    }
  }
})

