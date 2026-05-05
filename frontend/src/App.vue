<template>
  <div class="app-shell" :class="{ 'is-auth': !isLogin }">
    <header class="top-bar" :class="{ 'auth-top': !isLogin }">
      <div class="brand">
        <span class="dot"></span>
        <span class="title">IdeaLab</span>
      </div>
      <div class="top-actions">
        <template v-if="isLogin">
          <el-tag round effect="dark" type="info" class="user-tag">
            {{ auth.userId }}
          </el-tag>
          <el-button class="pill ghost" @click="handleLogout">退出</el-button>
        </template>
      </div>
    </header>

    <!-- 未登录：极简登录/注册面板 -->
    <div v-if="!isLogin" class="auth-hero">
      <div class="auth-glow"></div>
      <div class="auth-center">
        <div class="auth-greeting">欢迎回来，开始你的灵感旅程</div>
        <div class="auth-sub">请输入账号密码以登录，或快速注册一个新账户</div>
        <div class="auth-box">
          <el-tabs v-model="authTab" class="auth-tabs">
            <el-tab-pane label="登录" name="login">
              <el-form @submit.prevent="handleLogin" class="auth-form" label-position="top">
                <el-form-item label="账号">
                  <el-input 
                    v-model="loginForm.u" 
                    placeholder="请输入账号" 
                    size="large" 
                    class="auth-input"
                  >
                    <template #prefix>
                      <el-icon><User /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
                <el-form-item label="密码">
                  <el-input
                    v-model="loginForm.p"
                    placeholder="请输入密码"
                    type="password"
                    size="large"
                    class="auth-input"
                  >
                    <template #prefix>
                      <el-icon><Lock /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
                <div class="terms-row mt12">
                  <el-checkbox v-model="agreeTerms">
                    我已阅读并同意
                    <a class="link" href="#" target="_blank" rel="noopener noreferrer">使用条款</a>
                    和
                    <a class="link" href="#" target="_blank" rel="noopener noreferrer">隐私政策</a>
                  </el-checkbox>
                </div>
                <el-button type="primary" class="primary pill full mt16" @click="handleLogin" :loading="loginLoading">
                  登录
                </el-button>
              </el-form>
            </el-tab-pane>
            <el-tab-pane label="注册" name="register">
              <el-form @submit.prevent="handleRegister" class="auth-form" label-position="top">
                <el-form-item label="账号">
                  <el-input 
                    v-model="regForm.u" 
                    placeholder="账号" 
                    size="large" 
                    class="auth-input"
                  >
                    <template #prefix>
                      <el-icon><User /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
                <el-form-item label="密码">
                  <el-input
                    v-model="regForm.p"
                    placeholder="密码"
                    type="password"
                    size="large"
                    class="auth-input"
                  >
                    <template #prefix>
                      <el-icon><Lock /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
                <el-button class="ghost pill full mt16" @click="handleRegister" :loading="registerLoading">注册</el-button>
              </el-form>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>

    <!-- 已登录：主布局 -->
    <div v-else class="layout">
      <!-- 左侧栏 -->
      <aside class="sidebar card sticky">
        <div class="user-block">
          <div class="avatar">{{ auth.userId?.slice(0, 1).toUpperCase() }}</div>
          <div>
            <div class="label">当前用户</div>
            <div class="user-name">{{ auth.userId }}</div>
          </div>
        </div>

        <div class="section">
          <el-button class="primary pill full" @click="showGeminiSearch = true">新的搜索</el-button>
        </div>

        <div class="section">
          <div class="section-title">我的收藏</div>
          <el-button class="primary pill full" @click="viewAllFavorites">查看全部收藏</el-button>
          <el-button class="ghost pill full mt8 notes-entry-btn" @click="openNotesPage">我的笔记</el-button>
          <div class="chips">
            <el-tag
              v-for="h in history"
              :key="h"
              class="chip"
              round
              @click="quickSearch(h)"
            >
              {{ h }}
            </el-tag>
          </div>
        </div>
      </aside>

      <!-- 中间和右侧区域容器 -->
      <div class="main-right-container">
        <!-- 简洁搜索界面（覆盖中间+右侧） -->
        <div v-if="showGeminiSearch" class="simple-search-overlay">
          <div class="simple-search-content">
            <!-- Logo -->
            <div class="logo-section">
              <div class="logo-icon">
                <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <!-- 灯泡主体（圆形） -->
                  <circle cx="40" cy="32" r="18" fill="#111" stroke="#111" stroke-width="2"/>
                  <!-- 灯泡内部高光 -->
                  <circle cx="40" cy="28" r="8" fill="#fff" opacity="0.3"/>
                  <!-- 灯泡底部（螺纹） -->
                  <rect x="34" y="48" width="12" height="8" rx="2" fill="#111"/>
                  <rect x="36" y="52" width="8" height="2" fill="#fff" opacity="0.3"/>
                  <!-- 光线效果 -->
                  <path d="M18 32L10 32" stroke="#111" stroke-width="2.5" stroke-linecap="round" opacity="0.6"/>
                  <path d="M70 32L62 32" stroke="#111" stroke-width="2.5" stroke-linecap="round" opacity="0.6"/>
                  <path d="M40 14L40 6" stroke="#111" stroke-width="2.5" stroke-linecap="round" opacity="0.6"/>
                  <path d="M40 50L40 58" stroke="#111" stroke-width="2.5" stroke-linecap="round" opacity="0.6"/>
                  <!-- 对角线光线 -->
                  <path d="M24 20L16 12" stroke="#111" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
                  <path d="M56 20L64 12" stroke="#111" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
                  <path d="M24 44L16 52" stroke="#111" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
                  <path d="M56 44L64 52" stroke="#111" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
                </svg>
              </div>
              <div class="logo-text">IdeaLab</div>
            </div>
            
            <div class="search-input-wrapper">
              <el-input
                v-model="searchText"
                placeholder="有没有用数据增强来做多模态命名实体识别的工作"
                size="large"
                class="simple-search-input"
                @keyup.enter="handleGeminiSearch"
              >
                <template #prefix>
                  <el-icon class="search-icon"><Search /></el-icon>
                </template>
                <template #append>
                  <el-button class="primary pill" @click="handleGeminiSearch">
                    <el-icon v-if="searchLoading" class="spin"><Loading /></el-icon>
                    <span v-else>搜索</span>
                  </el-button>
                </template>
              </el-input>
            </div>
            <div class="search-suggestions">
              <div class="suggestions-label">试试这些示例</div>
              <div class="suggestions-list">
                <el-button
                  v-for="s in geminiSuggestions"
                  :key="s"
                  class="suggestion-chip"
                  round
                  @click="handleGeminiSuggestion(s)"
                >
                  {{ s }}
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 正常内容区域 -->
        <template v-else>
          <!-- 中间主区域 -->
          <main class="main">
            <section class="hero card">
          <div class="hero-title">探索文献，像和实验室对话一样自然</div>
          <div class="hero-input">
            <el-input
              v-model="searchText"
              placeholder="输入你想要检索的主题、问题或关键词"
              size="large"
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prepend>
                <el-icon><Search /></el-icon>
              </template>
              <template #append>
                <el-button class="primary pill" @click="handleSearch">
                  <el-icon v-if="searchLoading" class="spin"><Loading /></el-icon>
                  <span v-else>深度检索</span>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="hero-sub">
            <div class="slider-block">
              <span class="label">年份范围</span>
              <el-slider v-model="years" range :min="2000" :max="2030" />
            </div>
            <div class="history-inline">
              <span class="label">最近搜索</span>
              <el-tag
                v-for="h in history.slice(0, 5)"
                :key="h + 'inline'"
                class="chip"
                round
                @click="quickSearch(h)"
              >
                {{ h }}
              </el-tag>
            </div>
          </div>
        </section>

        <section class="results card">
          <div class="results-head">
            <div class="label">结果</div>
            <div class="meta-text">
              共 {{ currentItems.length }} / {{ filtered.length }} 篇（页码 {{ search.page }} / {{
                search.totalPages
              }}）
            </div>
          </div>

          <div v-if="viewMode === 'favorites'" class="folder-banner">
            <div class="label">当前视图：我的收藏</div>
            <el-button class="ghost pill" size="small" @click="viewMode = 'search'">返回检索结果</el-button>
          </div>

          <div v-if="!currentItems.length" class="empty">暂无数据，请尝试新的检索。</div>

          <div v-for="paper in currentItems" :key="paper.id" class="paper-card">
            <div class="paper-top">
              <div>
                <a class="paper-title" :href="paper.url" target="_blank">{{ paper.title }}</a>
                <div class="paper-meta">
                  <span class="mono">{{ paper.year }}</span>
                  <span class="mono">{{ formatMonth(paper.month) }}</span>
                  <span class="mono">匹配度 {{ formatScore(paper.score) }}%</span>
                </div>
              </div>
              <div class="actions">
                <el-select
                  v-if="!paper.is_favorited"
                  v-model="selectFolderMap[paper.id]"
                  placeholder="选择收藏夹"
                  size="small"
                  class="folder-select"
                >
                  <el-option v-for="f in fav.folders" :key="f" :label="f" :value="f" />
                </el-select>
                <el-button
                  class="pill"
                  :type="paper.is_favorited ? 'primary' : 'default'"
                  @click="toggleFav(paper, selectFolderMap[paper.id])"
                >
                  {{ paper.is_favorited ? '已收藏' : '收藏' }}
                </el-button>
                <el-button class="pill" @click="openNoteDialog(paper)">笔记</el-button>
              </div>
            </div>

            <div
              v-if="paper.ai_summary && paper.ai_summary.trim()"
              class="ai-summary"
              v-html="paper.ai_summary"
            />
            <div class="abstract">
              摘要：{{ (paper.abstract || '').slice(0, 320) }}...
            </div>
          </div>

          <div class="pager" v-if="filtered.length > search.pageSize">
            <el-pagination
              layout="prev, pager, next"
              :total="filtered.length"
              :page-size="search.pageSize"
              :current-page="search.page"
              @current-change="handlePageChange"
            />
          </div>
        </section>
      </main>

      <!-- 右侧栏 -->
      <aside v-if="isLogin" class="right">
        <section class="filters card sticky">
          <div class="section-title">筛选</div>
          <el-select v-model="localFilter.sort" class="full" placeholder="排序">
            <el-option label="相关性" value="相关性" />
            <el-option label="时间：新→旧" value="时间: 新→旧" />
            <el-option label="时间：旧→新" value="时间: 旧→新" />
          </el-select>
          <div class="mt12">
            <span class="label">年份</span>
            <el-slider v-model="localFilter.years" range :min="2000" :max="2030" />
          </div>
          <div class="mt12">
            <span class="label">月份</span>
            <el-select v-model="localFilter.months" multiple filterable class="full" placeholder="选择月份">
              <el-option v-for="m in monthOptions" :key="m" :label="m" :value="m" />
            </el-select>
          </div>
          <el-button class="primary pill full mt16" @click="applyFilters">应用筛选</el-button>
        </section>

        <section class="chat card sticky">
          <div class="section-title">AI 对话</div>
          <div class="chat-history" ref="chatBox">
            <div class="bubble assistant strong" v-if="!chat.history.length">
              你好，我可以帮你总结、对比、提炼结论。
              <div class="hint small">试着问：这批论文的核心贡献是什么？</div>
            </div>
            <div
              v-for="(m, i) in chat.history"
              :key="i"
              :class="['bubble', m.role]"
            >
              {{ m.content }}
            </div>
            <div v-if="aiThinking" class="bubble assistant loading">
              AI 正在思考
              <span class="dotting">...</span>
            </div>
          </div>
          <div class="suggestions">
            <el-tag v-for="s in suggestions" :key="s" class="chip" round @click="ask(s)">
              {{ s }}
            </el-tag>
          </div>
          <el-input
            v-model="prompt"
            type="textarea"
            :rows="3"
            placeholder="在这里提问，获取洞见"
            class="mt8"
          />
          <el-button class="primary pill full mt12" @click="ask(prompt)" :loading="aiThinking">
            发送
          </el-button>
        </section>
      </aside>
        </template>
      </div>
    </div>

    <!-- 收藏全屏页 -->
    <div v-if="showFavoritesPage" class="fav-overlay">
      <div class="fav-card">
        <div class="fav-head">
          <div class="fav-title">
            <el-button v-if="selectedFolder" class="ghost pill" size="small" @click="selectedFolder = null">
              ← 返回
            </el-button>
            <span v-else>我的收藏</span>
            <span v-if="selectedFolder" class="ml12">{{ selectedFolder }}</span>
          </div>
          <el-button class="ghost pill" size="small" @click="closeFavoritesPage">关闭</el-button>
        </div>
        
        <!-- 收藏夹列表视图 -->
        <div v-if="!selectedFolder" class="fav-folders">
          <div class="folder-actions">
            <el-input
              v-model="newFolderName"
              placeholder="输入新收藏夹名称"
              size="large"
              class="folder-input"
              @keyup.enter="createFolder"
            />
            <el-button class="primary pill" @click="createFolder">添加收藏夹</el-button>
          </div>
          <div class="folder-list">
            <div v-if="!fav.folders.length" class="empty">还没有收藏夹</div>
            <div v-for="folder in fav.folders" :key="folder" class="folder-item">
              <div class="folder-info" @click="selectedFolder = folder">
                <div class="folder-name">{{ folder }}</div>
                <div class="folder-count">
                  {{ fav.items.filter(p => (p.folder || '默认收藏夹') === folder).length }} 篇论文
                </div>
              </div>
              <el-button
                v-if="folder !== '默认收藏夹'"
                class="ghost pill"
                size="small"
                @click="deleteFolder(folder)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>

        <!-- 论文列表视图 -->
        <div v-else class="fav-list">
          <div v-if="!folderPapers.length" class="empty">此收藏夹还没有内容</div>
          <div v-for="paper in folderPapers" :key="paper.id" class="paper-card">
            <div class="paper-top">
  <div>
                <a class="paper-title" :href="paper.url" target="_blank">{{ paper.title }}</a>
                <div class="paper-meta">
                  <span class="mono">{{ paper.year }}</span>
                  <span class="mono">{{ formatMonth(paper.month) }}</span>
                </div>
              </div>
              <el-button class="pill" type="primary" @click="toggleFav(paper, paper.folder)">移除</el-button>
            </div>
            <div class="abstract">
              摘要：{{ (paper.abstract || '').slice(0, 320) }}...
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showNotesPage" class="fav-overlay">
      <div class="fav-card">
        <div class="fav-head">
          <div class="fav-title">我的笔记（{{ notesTotal }}）</div>
          <el-button class="ghost pill" size="small" @click="closeNotesPage">关闭</el-button>
        </div>

        <div class="folder-actions">
          <el-input
            v-model="notesKeyword"
            placeholder="按笔记内容搜索"
            size="large"
            class="folder-input"
            @keyup.enter="searchNotes"
          />
          <el-button class="primary pill" @click="searchNotes">搜索</el-button>
          <el-button class="ghost pill" @click="exportMyNotes">导出.md</el-button>
        </div>

        <div class="fav-list">
          <div v-if="notesLoading" class="empty">正在加载...</div>
          <div v-else-if="!notesItems.length" class="empty">暂无笔记</div>
          <div v-for="n in notesItems" :key="`${n.user_id}-${n.paper_id}`" class="paper-card">
              <div class="paper-top">
                <div>
                  <a
                    v-if="n.paper_url"
                    class="paper-title"
                    :href="n.paper_url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {{ n.paper_title || ('Paper #' + n.paper_id) }}
                  </a>
                  <div v-else class="paper-title">{{ n.paper_title || ('Paper #' + n.paper_id) }}</div>
                  <div class="paper-meta">
                    <span class="mono">论文ID {{ n.paper_id }}</span>
                    <span class="mono">更新时间 {{ n.updated_at ? new Date(n.updated_at).toLocaleString() : '-' }}</span>
                  </div>
                </div>
                <div class="actions">
                  <el-button class="pill" type="primary" plain @click="locatePaperFromNote(n)">定位论文</el-button>
                  <el-button class="pill" @click="editNoteFromList(n)">继续编辑</el-button>
                  <el-button class="pill" type="danger" @click="removeNoteFromList(n)">删除</el-button>
                </div>
              </div>
            <div class="abstract">
              {{ (n.content || '').slice(0, 260) || '（空笔记）' }}
            </div>
          </div>
          <div class="pager" v-if="notesTotal > notesPageSize">
            <el-pagination
              layout="prev, pager, next, total"
              :total="notesTotal"
              :page-size="notesPageSize"
              :current-page="notesPage"
              @current-change="handleNotesPageChange"
            />
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showNoteDialog" width="720" :title="`笔记 - ${notePaperTitle}`">
      <el-input
        v-model="noteContent"
        type="textarea"
        :rows="12"
        :disabled="noteLoading"
        placeholder="记录你的阅读摘要、疑问、结论..."
      />
      <template #footer>
        <el-button @click="showNoteDialog = false">关闭</el-button>
        <el-button type="primary" :loading="noteSaving" @click="saveCurrentNote">保存笔记</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, reactive, nextTick } from 'vue'
import { Search, Loading, User, Lock } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from './store/auth'
import { useSearchStore } from './store/search'
import { useFavStore } from './store/fav'
import { useChatStore } from './store/chat'
import {
  fetchHistory,
  chat as chatApi,
  fetchNote,
  saveNote,
  listNotes,
  deleteNote,
  exportNotesMarkdown,
  fetchPaperById
} from './services/api'

const auth = useAuthStore()
const search = useSearchStore()
const fav = useFavStore()
const chat = useChatStore()

const isLogin = computed(() => !!auth.userId)

const authTab = ref('login')
const loginForm = ref({ u: '', p: '' })
const agreeTerms = ref(false)
const regForm = ref({ u: '', p: '' })
const searchText = ref('')
const years = ref([2018, 2025])
const history = ref([])
const viewMode = ref('search')
const prompt = ref('')
const suggestions = ['推荐优先阅读的3篇论文并说明理由']
const chatBox = ref(null)
const searchLoading = ref(false)
const aiThinking = ref(false)
const showFavoritesPage = ref(false)
const selectedFolder = ref(null)
const newFolderName = ref('')
const selectFolderMap = reactive({})
const showGeminiSearch = ref(false)
// 控制筛选触发时不弹出“找到 X 篇”提示
const skipResultToast = ref(false)
const loginLoading = ref(false)
const registerLoading = ref(false)
const showNoteDialog = ref(false)
const noteLoading = ref(false)
const noteSaving = ref(false)
const notePaperId = ref(null)
const notePaperTitle = ref('')
const notePaperUrl = ref('')
const noteContent = ref('')
const showNotesPage = ref(false)
const notesItems = ref([])
const notesLoading = ref(false)
const notesKeyword = ref('')
const notesPage = ref(1)
const notesPageSize = ref(20)
const notesTotal = ref(0)
const geminiSuggestions = [
  '有没有用数据增强来做多模态命名实体识别的工作',
  '哪些论文使用了HotpotQA数据集',
  '使用强化学习算法进行训练是否能减少幻觉的论文',
  '关于非线性多智能体系统最优编队控制的论文',
  '基于Transformer的视觉-语言预训练模型对比研究'
]

const localFilter = ref({
  sort: '相关性',
  years: [2018, 2025],
  months: []
})

const filtered = computed(() => {
  if (viewMode.value === 'favorites') {
    return fav.items
  }
  return search.filtered
})

const currentItems = computed(() => search.pageItems)

// 月份英文到中文的映射
const monthMap = {
  'January': '一月',
  'February': '二月',
  'March': '三月',
  'April': '四月',
  'May': '五月',
  'June': '六月',
  'July': '七月',
  'August': '八月',
  'September': '九月',
  'October': '十月',
  'November': '十一月',
  'December': '十二月',
  'Jan': '一月',
  'Feb': '二月',
  'Mar': '三月',
  'Apr': '四月',
  'May': '五月',
  'Jun': '六月',
  'Jul': '七月',
  'Aug': '八月',
  'Sep': '九月',
  'Oct': '十月',
  'Nov': '十一月',
  'Dec': '十二月'
}

// 月份到数字的映射（用于排序）
const monthToNumber = (month) => {
  const monthNumMap = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
    'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12,
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
    '一月': 1, '二月': 2, '三月': 3, '四月': 4, '五月': 5, '六月': 6,
    '七月': 7, '八月': 8, '九月': 9, '十月': 10, '十一月': 11, '十二月': 12
  }
  return monthNumMap[month] || 0
}

const monthOptions = computed(() => {
  const set = new Set((search.results || []).map((p) => {
    if (!p.month) return null
    // 如果已经是中文，直接返回；否则转换为中文
    return monthMap[p.month] || p.month
  }).filter(Boolean))
  // 按月份数字排序
  return Array.from(set).sort((a, b) => {
    const numA = monthToNumber(a)
    const numB = monthToNumber(b)
    return numA - numB
  })
})

const folderPapers = computed(() => {
  if (!selectedFolder.value) return []
  return fav.items.filter((p) => (p.folder || '默认收藏夹') === selectedFolder.value)
})

// 将月份转换为中文显示
const formatMonth = (month) => {
  if (!month) return '未标注'
  return monthMap[month] || month
}

// 格式化匹配度分数显示
const formatScore = (score) => {
  if (score === null || score === undefined) return '0.0'
  const num = typeof score === 'string' ? parseFloat(score) : score
  if (isNaN(num)) return '0.0'
  return num.toFixed(1)
}

const handleLogin = async () => {
  if (!loginForm.value.u || !loginForm.value.p) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  if (!agreeTerms.value) {
    ElMessage.warning('请先阅读并同意使用条款和隐私政策')
    return
  }
  loginLoading.value = true
  try {
    const result = await auth.doLogin(loginForm.value.u, loginForm.value.p)
    if (result.success) {
      ElMessage.success('登录成功')
      await afterLogin()
      loginForm.value.u = ''
      loginForm.value.p = ''
      agreeTerms.value = false
    } else {
      ElMessage.error(result.error || '登录失败')
    }
  } catch (error) {
    ElMessage.error('登录失败，请稍后重试')
    console.error('Login error:', error)
  } finally {
    loginLoading.value = false
  }
}

const handleRegister = async () => {
  if (!regForm.value.u || !regForm.value.p) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  if (regForm.value.p.length < 6) {
    ElMessage.warning('密码长度至少为6位')
    return
  }
  registerLoading.value = true
  try {
    const result = await auth.doRegister(regForm.value.u, regForm.value.p)
    if (result.success) {
      ElMessage.success('注册成功，请登录')
      regForm.value.u = ''
      regForm.value.p = ''
      authTab.value = 'login'
    } else {
      ElMessage.error(result.error || '注册失败')
    }
  } catch (error) {
    ElMessage.error('注册失败，请稍后重试')
    console.error('Register error:', error)
  } finally {
    registerLoading.value = false
  }
}

const handleLogout = () => {
  auth.logout()
  fav.folders = ['默认收藏夹']
  fav.items = []
  fav.current = '默认收藏夹'
  search.results = []
  search.filters = { sort: '相关性', years: [2018, 2025], months: [] }
  search.page = 1
  search.lastQuery = ''
  chat.reset()
  history.value = []
  searchText.value = ''
  showGeminiSearch.value = false
}

const afterLogin = async () => {
  await fav.load(auth.userId)
  loadHistory()
  showGeminiSearch.value = true
}

const loadHistory = async () => {
  try {
    const r = await fetchHistory(auth.userId)
    history.value = r.data || []
  } catch (e) {
    history.value = []
  }
}

const handleSearch = async () => {
  if (!searchText.value) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  showGeminiSearch.value = false
  viewMode.value = 'search'
  searchLoading.value = true
  try {
    await search.doSearch(searchText.value, years.value[0], years.value[1], auth.userId)
    search.filters = { ...localFilter.value }
    if (!history.value.includes(searchText.value)) history.value.unshift(searchText.value)
    
    // 搜索时后端已经为第一页生成了推荐原因，这里不需要额外处理，然后推荐原因会逐个出现
    
    // 仅在非筛选触发时提示
    const shouldToast = !skipResultToast.value
    skipResultToast.value = false

    if (shouldToast) {
      if (search.results.length === 0) {
        ElMessage.warning('未找到匹配的论文，请尝试其他关键词')
      } else {
        ElMessage.success(`找到 ${search.results.length} 篇论文`)
      }
    }
  } catch (error) {
    ElMessage.error('搜索失败，请稍后重试')
    console.error('Search error:', error)
    console.error('Error response:', error?.response)
  } finally {
    searchLoading.value = false
  }
}

const quickSearch = (q) => {
  searchText.value = q
  handleSearch()
}

const handleGeminiSearch = async () => {
  if (!searchText.value) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  showGeminiSearch.value = false
  viewMode.value = 'search'
  searchLoading.value = true
  try {
    await search.doSearch(searchText.value, years.value[0], years.value[1], auth.userId)
    search.filters = { ...localFilter.value }
    if (!history.value.includes(searchText.value)) history.value.unshift(searchText.value)
    
    // 仅在非筛选触发时提示
    const shouldToast = !skipResultToast.value
    skipResultToast.value = false

    if (shouldToast) {
      if (search.results.length === 0) {
        ElMessage.warning('未找到匹配的论文，请尝试其他关键词')
      } else {
        ElMessage.success(`找到 ${search.results.length} 篇论文`)
      }
    }
  } catch (error) {
    ElMessage.error('搜索失败，请稍后重试')
    console.error('Search error:', error)
    console.error('Error response:', error?.response)
  } finally {
    searchLoading.value = false
  }
}

const handleGeminiSuggestion = (suggestion) => {
  searchText.value = suggestion
  handleGeminiSearch()
}

const toggleFav = async (paper, folder) => {
  const targetFolder = folder || fav.current || '默认收藏夹'
  try {
    await fav.toggle(auth.userId, paper, targetFolder)
    if (paper.is_favorited) {
      ElMessage.success('已添加到收藏')
    } else {
      ElMessage.success('已取消收藏')
    }
  } catch (error) {
    ElMessage.error('操作失败，请稍后重试')
    console.error('Toggle favorite error:', error)
  }
}

const viewAllFavorites = () => {
  viewMode.value = 'favorites'
  showFavoritesPage.value = true
  selectedFolder.value = null
  search.page = 1
}

const closeFavoritesPage = () => {
  showFavoritesPage.value = false
  selectedFolder.value = null
  newFolderName.value = ''
}

const loadAllNotes = async () => {
  if (!auth.userId) return
  notesLoading.value = true
  try {
    const r = await listNotes(auth.userId, notesPage.value, notesPageSize.value, notesKeyword.value || '')
    notesItems.value = r?.data?.items || []
    notesTotal.value = r?.data?.total || 0
  } catch (e) {
    ElMessage.error('加载笔记列表失败')
  } finally {
    notesLoading.value = false
  }
}

const openNotesPage = async () => {
  showNotesPage.value = true
  notesPage.value = 1
  await loadAllNotes()
}

const closeNotesPage = () => {
  showNotesPage.value = false
}

const searchNotes = async () => {
  notesPage.value = 1
  await loadAllNotes()
}

const handleNotesPageChange = async (p) => {
  notesPage.value = p
  await loadAllNotes()
}

const editNoteFromList = async (note) => {
  showNotesPage.value = false
  await openNoteDialog({
    id: note.paper_id,
    title: note.paper_title || `Paper #${note.paper_id}`,
    url: note.paper_url || ''
  })
}

const locatePaperFromNote = async (note) => {
  if (note.paper_url) {
    window.open(note.paper_url, '_blank', 'noopener,noreferrer')
    return
  }
  try {
    const r = await fetchPaperById(note.paper_id)
    const paper = r?.data || {}
    if (paper?.url) {
      window.open(paper.url, '_blank', 'noopener,noreferrer')
      return
    }
    if (paper?.title) {
      showNotesPage.value = false
      searchText.value = paper.title
      await handleSearch()
      ElMessage.info('已按论文标题定位到检索结果')
      return
    }
  } catch (e) {
    // fallback below
  }
  if (note.paper_title) {
    showNotesPage.value = false
    searchText.value = note.paper_title
    await handleSearch()
    ElMessage.info('已按标题定位到论文检索结果')
    return
  }
  ElMessage.warning('该笔记缺少论文定位信息')
}

const exportMyNotes = async () => {
  try {
    const r = await exportNotesMarkdown(auth.userId)
    const text = r?.data || ''
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${auth.userId}-notes.md`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('笔记已导出')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

const removeNoteFromList = async (note) => {
  try {
    await ElMessageBox.confirm(
      '确定删除这条笔记吗？删除后不可恢复。',
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteNote(auth.userId, note.paper_id)
    ElMessage.success('笔记已删除')
    await loadAllNotes()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除笔记失败')
    }
  }
}

const openNoteDialog = async (paper) => {
  if (!auth.userId) {
    ElMessage.warning('请先登录')
    return
  }
  const pid = Number(paper.id)
  if (Number.isNaN(pid)) {
    ElMessage.warning('当前论文ID无效，无法记录笔记')
    return
  }
  notePaperId.value = pid
  notePaperTitle.value = paper.title || `Paper #${pid}`
  notePaperUrl.value = paper.url || ''
  noteContent.value = ''
  showNoteDialog.value = true
  noteLoading.value = true
  try {
    const r = await fetchNote(auth.userId, pid)
    noteContent.value = r?.data?.content || ''
  } catch (e) {
    ElMessage.error('读取笔记失败')
  } finally {
    noteLoading.value = false
  }
}

const saveCurrentNote = async () => {
  if (notePaperId.value === null || notePaperId.value === undefined) return
  noteSaving.value = true
  try {
    await saveNote(
      auth.userId,
      notePaperId.value,
      noteContent.value || '',
      notePaperTitle.value || '',
      notePaperUrl.value || ''
    )
    ElMessage.success('笔记已保存')
    if (showNotesPage.value) {
      await loadAllNotes()
    }
  } catch (e) {
    ElMessage.error('保存笔记失败')
  } finally {
    noteSaving.value = false
  }
}

const createFolder = async () => {
  if (!newFolderName.value.trim()) {
    ElMessage.warning('请输入收藏夹名称')
    return
  }
  if (fav.folders.includes(newFolderName.value.trim())) {
    ElMessage.warning('收藏夹已存在')
    return
  }
  try {
    await fav.createFolder(auth.userId, newFolderName.value.trim())
    ElMessage.success('收藏夹创建成功')
    newFolderName.value = ''
  } catch (error) {
    ElMessage.error('创建失败，请稍后重试')
    console.error('Create folder error:', error)
  }
}

const deleteFolder = async (folderName) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除收藏夹"${folderName}"吗？此操作会同时删除该收藏夹中的所有论文。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await fav.removeFolder(auth.userId, folderName)
    ElMessage.success('收藏夹已删除')
    if (selectedFolder.value === folderName) {
      selectedFolder.value = null
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败，请稍后重试')
      console.error('Delete folder error:', error)
    }
  }
}

const applyFilters = () => {
  search.filters = { ...localFilter.value }
  search.page = 1
  // 直接提示筛选后的结果数量
  const count = filtered.value.length
  ElMessage.info(`根据筛选条件找到 ${count} 篇论文`)
}

const ask = async (q) => {
  if (!q || !q.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  const plain = q.trim()
  const userMsg = { role: 'user', content: plain }
  chat.history.push(userMsg)
  prompt.value = ''
  aiThinking.value = true
  if (chatBox.value) chatBox.value.scrollTo({ top: chatBox.value.scrollHeight, behavior: 'smooth' })
  try {
    // 仅发送精简上下文，减少 payload
    const context = filtered.value.slice(0, 8).map((p) => ({
      title: p.title,
      year: p.year,
      abstract: (p.abstract || '').slice(0, 800),
      ai_summary: p.ai_summary ? p.ai_summary.slice(0, 800) : '',
      dataset: p.dataset || '',
      model: p.model || ''
    }))

    const { data } = await chatApi(plain, context)
    const full = (data?.response || '').trim()
    const answer = full.length > 0 ? full : '抱歉，暂时无法获取回答。'

    // 确保先推送一条助手消息，再做打字动画，避免空内容时没有回复
    chat.history.push({ role: 'assistant', content: '' })
    let shown = ''
    const interval = setInterval(() => {
      if (shown.length < answer.length) {
        shown = answer.slice(0, shown.length + 6)
        chat.history[chat.history.length - 1].content = shown
      } else {
        clearInterval(interval)
      }
      if (chatBox.value) chatBox.value.scrollTo({ top: chatBox.value.scrollHeight, behavior: 'smooth' })
    }, 30)
  } catch (e) {
    console.error('Chat error:', e)
    chat.history.push({ role: 'assistant', content: '抱歉，暂时无法获取回答。请稍后重试。' })
    ElMessage.error('AI对话失败，请稍后重试')
  } finally {
    aiThinking.value = false
  }
}

const handlePageChange = async (newPage) => {
  search.page = newPage
  // 等待页面更新
  await nextTick()
  // 换页时为当前页生成推荐原因
  if (search.currentQuery && currentItems.value.length > 0) {
    // 检查当前页是否有论文缺少推荐原因
    const hasMissingSummary = currentItems.value.some(p => !p.ai_summary || !p.ai_summary.trim())
    if (hasMissingSummary) {
      // 为当前页的论文生成推荐原因
      await search.generatePageSummaries()
    }
  }
}

watch(
  () => auth.userId,
  (val) => {
    if (val) afterLogin()
  },
  { immediate: true }
)

onMounted(() => {
  document.documentElement.style.setProperty('--el-color-primary', '#111111')
  document.documentElement.style.setProperty('--el-color-primary-dark-2', '#000000')
  document.documentElement.style.setProperty('--el-color-primary-light-3', '#3a3a3a')
})
</script>

<style scoped>
:global(body) {
  background: #f7f9fc;
  color: #0f0f0f;
  font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.app-shell.is-auth :global(body) {
  background: #f7f9fc;
  color: #0f0f0f;
}
:global(.el-button),
:global(.el-input__wrapper),
:global(.el-card),
:global(.el-select .el-input__wrapper) {
  border-radius: 12px !important;
}
:global(.el-button) {
  transition: all 0.3s ease;
}
:global(.el-button:active) {
  transform: scale(0.98);
}
:global(.el-pagination.is-background .el-pager li.is-active) {
  background-color: #111 !important;
  color: #fff !important;
}

.app-shell {
  min-height: 100vh;
  background: linear-gradient(180deg, #eef5ff 0%, #f3f8ff 100%);
}
.app-shell.is-auth {
  background: linear-gradient(180deg, #ffffff 0%, #f5f7fb 100%);
}
.top-bar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #e6e6e6;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 10;
}
.top-bar.auth-top {
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dot {
  width: 12px;
  height: 12px;
  background: #000;
  border-radius: 50%;
}
.title {
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #000;
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-tag {
  background: #111;
  color: #fff;
  border-radius: 999px;
}

.auth-hero {
  position: relative;
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0f0f0f;
  overflow: hidden;
}
.auth-glow {
  position: absolute;
  width: 700px;
  height: 700px;
  background: radial-gradient(circle, rgba(33, 150, 243, 0.08), transparent 55%);
  filter: blur(50px);
  z-index: 0;
}
.auth-center {
  position: relative;
  z-index: 1;
  width: 640px;
  text-align: center;
  padding: 24px;
}
.auth-greeting {
  font-size: 36px;
  font-weight: 800;
  margin-bottom: 12px;
  color: #111;
}
.auth-sub {
  color: #4b5563;
  margin-bottom: 24px;
}
.auth-box {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  padding: 20px;
  backdrop-filter: blur(8px);
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.12);
}
.auth-tabs :global(.el-tabs__item.is-active) {
  color: #111;
}
.auth-tabs :global(.el-tabs__nav-wrap::after) {
  background: rgba(0, 0, 0, 0.06);
}
.auth-tabs :global(.el-tabs__item) {
  color: rgba(0, 0, 0, 0.6);
}
.auth-tabs :global(.el-tabs__item:hover) {
  color: rgba(0, 0, 0, 0.9);
}
.auth-box :global(.el-input__wrapper) {
  background: #f8fafc !important;
  border: 1px solid #e5e7eb !important;
  box-shadow: none !important;
}
.auth-box :global(.el-input__wrapper:hover) {
  border-color: #cbd5e1 !important;
}
.auth-box :global(.el-input__wrapper.is-focus) {
  border-color: #111 !important;
  box-shadow: 0 0 0 2px rgba(17, 17, 17, 0.08) !important;
}
.auth-box :global(.el-input__inner) {
  color: #0f172a !important;
  background: transparent !important;
}
.auth-box :global(.el-input__inner::placeholder) {
  color: rgba(15, 23, 42, 0.4) !important;
}
.auth-form {
  margin-top: 16px;
  max-width: 680px;
  margin-left: auto;
  margin-right: auto;
}
.auth-row {
  display: flex;
  align-items: center;
  gap: 0;
}
.field-label {
  font-size: 14px;
  font-weight: 600;
  color: #111;
  text-align: right;
  min-width: 38px;
  padding-right: 0;
}
.auth-input {
  width: 100%;
  display: block;
  flex: 1;
}
.auth-input :global(.el-input__wrapper) {
  min-height: 40px;
  padding: 0 12px;
  width: 100%;
}
.auth-input :global(.el-input__inner) {
  height: 36px;
  line-height: 36px;
}
.auth-form :global(.el-form-item) {
  margin-bottom: 12px;
}
.auth-form :global(.el-form-item__label) {
  padding: 0;
  margin-bottom: 4px;
  line-height: 18px;
  font-weight: 600;
  color: #111;
}
.auth-box :global(.el-input) {
  width: 100%;
  display: block;
}
.terms-row {
  text-align: left;
  color: #111;
  font-size: 13px;
  line-height: 1.6;
}
.terms-row .link {
  color: #111;
  text-decoration: underline;
  margin: 0 2px;
}

.layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  padding: 16px;
  height: calc(100vh - 64px);
  overflow: hidden;
}
.main-right-container {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
  height: calc(100vh - 80px);
  overflow: hidden;
  position: relative;
}
.card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.04);
  border: 1px solid #efefef;
  color: #000;
}
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 80px;
  height: calc(100vh - 80px);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: #d0d0d0 transparent;
}
.sidebar::-webkit-scrollbar {
  width: 6px;
}
.sidebar::-webkit-scrollbar-track {
  background: transparent;
}
.sidebar::-webkit-scrollbar-thumb {
  background: #d0d0d0;
  border-radius: 3px;
}
.sidebar::-webkit-scrollbar-thumb:hover {
  background: #b0b0b0;
}
.user-block {
  display: flex;
  gap: 12px;
  align-items: center;
}
.avatar {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #111;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}
.label {
  font-size: 12px;
  color: #555;
  font-weight: 500;
}
.user-name {
  font-weight: 700;
  color: #000;
}
.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.section-title {
  font-weight: 700;
  color: #000;
  font-size: 15px;
}
.folders {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.folder-btn {
  padding: 6px 12px;
}
.folder-create {
  display: flex;
  gap: 8px;
  align-items: center;
}
.chips {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.chip {
  cursor: pointer;
  border-radius: 999px;
  max-width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  padding: 6px 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - 80px);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: #d0d0d0 transparent;
}
.main::-webkit-scrollbar {
  width: 6px;
}
.main::-webkit-scrollbar-track {
  background: transparent;
}
.main::-webkit-scrollbar-thumb {
  background: #d0d0d0;
  border-radius: 3px;
}
.main::-webkit-scrollbar-thumb:hover {
  background: #b0b0b0;
}

.simple-search-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 16px;
  z-index: 10;
}
.simple-search-content {
  width: 100%;
  max-width: 900px;
  padding: 60px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 40px;
}
.logo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  margin-bottom: 10px;
}
.logo-icon {
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: float 3s ease-in-out infinite;
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.1));
}
.logo-icon svg {
  width: 100%;
  height: 100%;
}
.logo-text {
  font-size: 42px;
  font-weight: 800;
  color: #111;
  letter-spacing: 3px;
  font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: linear-gradient(135deg, #111 0%, #333 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-8px);
  }
}
.search-input-wrapper {
  width: 100%;
}
.simple-search-input :global(.el-input__wrapper) {
  background: #fff !important;
  border: 2px solid #e0e0e0 !important;
  border-radius: 12px !important;
  padding: 16px 20px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
  transition: all 0.3s ease !important;
}
.simple-search-input :global(.el-input__wrapper:hover) {
  border-color: #b0b0b0 !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
}
.simple-search-input :global(.el-input__wrapper.is-focus) {
  border-color: #111 !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12) !important;
}
.simple-search-input :global(.el-input__inner) {
  color: #000 !important;
  font-size: 16px !important;
}
.simple-search-input :global(.el-input__inner::placeholder) {
  color: #999 !important;
}
.search-icon {
  color: #666;
  font-size: 20px;
}
.search-suggestions {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.suggestions-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}
.suggestions-list {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-start;
}
.suggestion-chip {
  background: #f5f5f5 !important;
  border: 1px solid #e0e0e0 !important;
  color: #333 !important;
  padding: 10px 18px !important;
  font-size: 14px !important;
  transition: all 0.3s ease !important;
  white-space: nowrap;
}
.suggestion-chip:hover {
  background: #eeeeee !important;
  border-color: #b0b0b0 !important;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
}
.hero-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 12px;
  color: #000;
}
.hero-input {
  margin-bottom: 12px;
}
.hero-sub {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.slider-block {
  min-width: 260px;
  flex: 1;
}
.history-inline {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.results-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.results-head .label {
  font-size: 16px;
  font-weight: 700;
  color: #000;
}
.meta-text {
  color: #555;
  font-size: 13px;
}
.folder-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f5f5f5;
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.folder-banner .label {
  font-size: 14px;
  font-weight: 600;
  color: #000;
}
.paper-card {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid #eee;
  background: #fff;
  margin-bottom: 12px;
  transition: all 0.3s ease;
}
.paper-card:hover {
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}
.paper-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.folder-select {
  width: 150px;
}
.paper-title {
  font-weight: 700;
  font-size: 16px;
  color: #000;
  text-decoration: none;
}
.paper-title:hover {
  color: #333;
  text-decoration: underline;
}
.paper-meta {
  display: flex;
  gap: 12px;
  margin-top: 4px;
  color: #555;
}
.mono {
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
}
.ai-summary {
  margin: 10px 0;
  padding: 12px;
  border-radius: 12px;
  background: #f7f7f7;
  border: 1px dashed #dcdcdc;
  color: #111;
}
.abstract {
  color: #444;
  line-height: 1.6;
}
.empty {
  padding: 24px;
  text-align: center;
  color: #888;
}
.pager {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}

.right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 80px;
  height: calc(100vh - 80px);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: #d0d0d0 transparent;
}
.right::-webkit-scrollbar {
  width: 6px;
}
.right::-webkit-scrollbar-track {
  background: transparent;
}
.right::-webkit-scrollbar-thumb {
  background: #d0d0d0;
  border-radius: 3px;
}
.right::-webkit-scrollbar-thumb:hover {
  background: #b0b0b0;
}
.filters {
  flex: 0 0 auto;
}
.chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}
.chat-history {
  flex: 1;
  border: 1px solid #efefef;
  border-radius: 12px;
  padding: 10px;
  background: #fafafa;
  overflow: auto;
}
.bubble {
  padding: 10px 12px;
  border-radius: 12px;
  margin-bottom: 8px;
  max-width: 100%;
  line-height: 1.5;
}
.bubble.user {
  background: #111;
  color: #fff;
  align-self: flex-end;
}
.bubble.assistant {
  background: #f0f0f0;
  color: #111;
  align-self: flex-start;
}
.suggestions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.hint {
  color: #888;
  font-size: 13px;
}

.primary {
  background: #111 !important;
  color: #fff !important;
  border: 1px solid #111 !important;
}
.ghost {
  background: #fff !important;
  color: #111 !important;
  border: 1px solid #e3e3e3 !important;
}
.pill {
  border-radius: 999px !important;
}
.full {
  width: 100%;
}
.notes-entry-btn {
  display: flex !important;
  width: 100% !important;
}
.mt8 {
  margin-top: 8px;
}
.mt12 {
  margin-top: 12px;
}
.mt16 {
  margin-top: 16px;
}

.fav-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  padding: 24px;
}
.fav-card {
  width: min(1100px, 95vw);
  max-height: 90vh;
  background: #fff;
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.16);
  overflow: auto;
}
.fav-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.fav-title {
  font-size: 18px;
  font-weight: 800;
  color: #000;
}
.fav-list {
  max-height: 70vh;
  overflow: auto;
}
.fav-folders {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.folder-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}
.folder-input {
  flex: 1;
}
.folder-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.folder-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 12px;
  border: 1px solid #e6e6e6;
  transition: all 0.3s ease;
  cursor: pointer;
}
.folder-item:hover {
  background: #f0f0f0;
  border-color: #d0d0d0;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}
.folder-info {
  flex: 1;
}
.folder-name {
  font-weight: 700;
  font-size: 16px;
  margin-bottom: 4px;
  color: #000;
}
.folder-count {
  font-size: 13px;
  color: #555;
}
.ml12 {
  margin-left: 12px;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
