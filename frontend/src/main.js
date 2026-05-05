import { createApp } from 'vue'
import { createPinia } from 'pinia' // 1. 引入 Pinia
import './style.css'
import App from './App.vue'

// 2. 创建 app 实例
const app = createApp(App)

// 3. 创建并挂载 Pinia
const pinia = createPinia()
app.use(pinia)

// 导入 Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
app.use(ElementPlus)

// 4. 最后再挂载到 #app
app.mount('#app')