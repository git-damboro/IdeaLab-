import axios from 'axios'

// 优先使用环境变量的完整地址，未配置时走 Vite 代理的 /api
const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 60000 // 增加到60秒，因为生成推荐原因可能需要较长时间
})

http.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error?.response?.data || error)
)

export default http

