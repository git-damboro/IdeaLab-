import http from './http'

export const login = (username, password) => {
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)
  return http.post('/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  })
}

export const register = (username, password) =>
  http.post('/auth/register', { username, password })

export const search = (payload) => http.post('/search', payload)

export const fetchFolders = (userId) => http.get(`/folders/${userId}`)
export const addFolder = (userId, name) =>
  http.post('/folders/add', { user_id: userId, folder_name: name })
export const deleteFolder = (userId, name) =>
  http.post('/folders/delete', { user_id: userId, folder_name: name })

export const fetchFavorites = (userId) => http.get(`/favorites/${userId}`)
export const addFavorite = (userId, paper, folder) =>
  http.post('/favorite/add', { user_id: userId, paper, folder_name: folder })
export const removeFavorite = (userId, paperId) =>
  http.post('/favorite/remove', { user_id: userId, paper_id: paperId })

export const fetchHistory = (userId) => http.get(`/history/${userId}`)

export const chat = (prompt, context) =>
  http.post('/chat', { user_query: prompt, context_papers: context })

export const batchGenerateSummary = (paperIds, userQuery, paperTitles = null) =>
  http.post('/paper/batch-summary', { 
    paper_ids: paperIds, 
    user_query: userQuery,
    paper_titles: paperTitles  // 传递标题列表，用于ID不匹配时通过标题匹配
  })

export const generateSingleSummary = (paperId, userQuery) =>
  http.post('/paper/summary', { paper_id: paperId, user_query: userQuery })

export const fetchNote = (userId, paperId) =>
  http.get('/api/v1/notes', { params: { user_id: userId, paper_id: paperId } })

export const saveNote = (userId, paperId, content, paperTitle = '', paperUrl = '') =>
  http.post('/api/v1/notes', {
    user_id: userId,
    paper_id: paperId,
    content,
    paper_title: paperTitle,
    paper_url: paperUrl
  })

export const listNotes = (userId, page = 1, pageSize = 50, keyword = '') =>
  http.get('/api/v1/notes/list', { params: { user_id: userId, page, page_size: pageSize, keyword } })

export const deleteNote = (userId, paperId) =>
  http.delete('/api/v1/notes', { params: { user_id: userId, paper_id: paperId } })

export const exportNotesMarkdown = (userId) =>
  http.get('/api/v1/notes/export.md', { params: { user_id: userId }, responseType: 'text' })

export const fetchPaperById = (paperId) =>
  http.get(`/api/v1/papers/${paperId}`)

