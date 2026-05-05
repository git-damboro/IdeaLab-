import { defineStore } from 'pinia'
import { search, batchGenerateSummary, generateSingleSummary } from '../services/api'

export const useSearchStore = defineStore('search', {
  state: () => ({
    results: [],
    filters: { sort: '相关性', years: [2018, 2025], months: [] },
    page: 1,
    pageSize: 10,
    lastQuery: '',
    currentQuery: '', // 保存当前搜索查询，用于生成推荐原因
    generatingSummaries: false, // 标记是否正在生成推荐原因，避免重复请求
    loadingPaperIds: [] // 正在加载推荐原因的论文ID数组（使用数组以便Vue追踪变化）
  }),
  getters: {
    filtered(state) {
      // 先按年份筛选
      // 注意：直接使用 filter，JavaScript 的 filter 会保留所有字段
      let arr = state.results.filter(
        (p) => p.year >= state.filters.years[0] && p.year <= state.filters.years[1]
      )
      
      // 月份筛选：如果不选择月份，显示所有月份；如果选择了月份，只显示选中的月份（取并集）
      if (state.filters.months.length > 0) {
        // 创建月份映射表（英文->中文）
        const monthMap = {
          'January': '一月', 'February': '二月', 'March': '三月', 'April': '四月',
          'May': '五月', 'June': '六月', 'July': '七月', 'August': '八月',
          'September': '九月', 'October': '十月', 'November': '十一月', 'December': '十二月',
          'Jan': '一月', 'Feb': '二月', 'Mar': '三月', 'Apr': '四月',
          'May': '五月', 'Jun': '六月', 'Jul': '七月', 'Aug': '八月',
          'Sep': '九月', 'Oct': '十月', 'Nov': '十一月', 'Dec': '十二月',
          // 支持小写
          'january': '一月', 'february': '二月', 'march': '三月', 'april': '四月',
          'may': '五月', 'june': '六月', 'july': '七月', 'august': '八月',
          'september': '九月', 'october': '十月', 'november': '十一月', 'december': '十二月',
          'jan': '一月', 'feb': '二月', 'mar': '三月', 'apr': '四月',
          'may': '五月', 'jun': '六月', 'jul': '七月', 'aug': '八月',
          'sep': '九月', 'oct': '十月', 'nov': '十一月', 'dec': '十二月'
        }
        
        // 创建反向映射（中文->英文完整形式）
        const reverseMonthMap = {
          '一月': ['January', 'Jan', 'january', 'jan'],
          '二月': ['February', 'Feb', 'february', 'feb'],
          '三月': ['March', 'Mar', 'march', 'mar'],
          '四月': ['April', 'Apr', 'april', 'apr'],
          '五月': ['May', 'may'],
          '六月': ['June', 'Jun', 'june', 'jun'],
          '七月': ['July', 'Jul', 'july', 'jul'],
          '八月': ['August', 'Aug', 'august', 'aug'],
          '九月': ['September', 'Sep', 'september', 'sep'],
          '十月': ['October', 'Oct', 'october', 'oct'],
          '十一月': ['November', 'Nov', 'november', 'nov'],
          '十二月': ['December', 'Dec', 'december', 'dec']
        }
        
        // 将选中的月份（可能是中文）转换为所有可能的表示形式
        const selectedMonthsSet = new Set()
        state.filters.months.forEach(month => {
          // 添加原始值（可能是中文）
          selectedMonthsSet.add(month)
          
          // 如果是中文，添加对应的所有英文形式（包括大小写变体）
          if (reverseMonthMap[month]) {
            reverseMonthMap[month].forEach(enMonth => {
              selectedMonthsSet.add(enMonth)
              // 也添加首字母大写的变体
              if (enMonth.length > 3) {
                selectedMonthsSet.add(enMonth.charAt(0).toUpperCase() + enMonth.slice(1).toLowerCase())
              }
            })
          }
          
          // 如果是英文，添加对应的中文
          if (monthMap[month]) {
            selectedMonthsSet.add(monthMap[month])
          }
          
          // 处理大小写变体
          const monthLower = month.toLowerCase()
          const monthCapitalized = month.charAt(0).toUpperCase() + month.slice(1).toLowerCase()
          if (monthMap[monthLower]) {
            selectedMonthsSet.add(monthMap[monthLower])
          }
          if (monthMap[monthCapitalized]) {
            selectedMonthsSet.add(monthMap[monthCapitalized])
          }
        })
        
        // 筛选：论文的月份（可能是英文）需要匹配选中的月份（可能是中文）
        arr = arr.filter((p) => {
          const pMonth = (p.month || '').trim()
          if (!pMonth) return false // 如果选择了月份但论文没有月份信息，不显示
          
          // 直接检查论文月份是否在选中集合中（包括所有变体）
          if (selectedMonthsSet.has(pMonth)) return true
          
          // 不区分大小写检查
          const pMonthLower = pMonth.toLowerCase()
          const pMonthCapitalized = pMonth.charAt(0).toUpperCase() + pMonth.slice(1).toLowerCase()
          if (selectedMonthsSet.has(pMonthLower)) return true
          if (selectedMonthsSet.has(pMonthCapitalized)) return true
          
          // 将论文月份转换为中文，检查是否匹配选中的中文月份
          const pMonthCN = monthMap[pMonth] || monthMap[pMonthLower] || monthMap[pMonthCapitalized]
          if (pMonthCN && state.filters.months.includes(pMonthCN)) return true
          
          // 如果论文月份已经是中文，直接检查是否在选中列表中
          if (state.filters.months.includes(pMonth)) return true
          
          return false
        })
      }
      // 如果不选择月份（months.length === 0），不进行月份筛选，显示所有论文
      
      // 月份到数字的映射（用于排序）
      const monthToNumber = (month) => {
        if (!month) return 0 // 没有月份信息返回0
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
      
      // 按时间排序（年份+月份）
      if (state.filters.sort === '时间: 新→旧') {
        arr = [...arr].sort((a, b) => {
          // 先按年份降序
          if (b.year !== a.year) return b.year - a.year
          // 同年按月份降序
          const monthA = monthToNumber(a.month)
          const monthB = monthToNumber(b.month)
          // 如果都没有月份信息，保持原顺序
          if (monthA === 0 && monthB === 0) return 0
          // 如果只有一个没有月份，没有月份的排在后面
          if (monthA === 0) return 1
          if (monthB === 0) return -1
          return monthB - monthA
        })
      } else if (state.filters.sort === '时间: 旧→新') {
        arr = [...arr].sort((a, b) => {
          // 先按年份升序
          if (a.year !== b.year) return a.year - b.year
          // 同年按月份升序
          const monthA = monthToNumber(a.month)
          const monthB = monthToNumber(b.month)
          // 如果都没有月份信息，保持原顺序
          if (monthA === 0 && monthB === 0) return 0
          // 如果只有一个没有月份，没有月份的排在后面
          if (monthA === 0) return 1
          if (monthB === 0) return -1
          return monthA - monthB
        })
      }
      // 相关性：按匹配度从高到低排序（默认排序）
      // 注意：后端返回的数据已经按相关性排序，这里只需要确保顺序一致
      if (state.filters.sort === '相关性' || !state.filters.sort) {
        const toScore = (paper) => {
          if (paper.score === null || paper.score === undefined) return 0
          const n = typeof paper.score === 'string' ? parseFloat(paper.score) : Number(paper.score)
          return Number.isNaN(n) ? 0 : n
        }
        // 后端已经按相关性排序，这里再次排序确保一致性
        arr = [...arr].sort((a, b) => {
          const scoreA = toScore(a)
          const scoreB = toScore(b)
          // 降序排序：分数高的在前
          return scoreB - scoreA
        })
        
        // 排序后，检查前10篇是否有推荐原因，如果没有则从原始 results 中恢复
        const first10AfterSort = arr.slice(0, 10)
        first10AfterSort.forEach((p, i) => {
          if (!p.ai_summary || !p.ai_summary.trim()) {
            // 从原始 results 中查找
            const original = state.results.find(r => r.id === p.id)
            if (original && original.ai_summary && original.ai_summary.trim()) {
              p.ai_summary = original.ai_summary
              console.log(`✅ 已从原始 results 恢复论文 ${p.id} 的推荐原因（排序后位置 ${i+1}）`)
            }
          }
        })
      }
      
      // 确保返回的数组中所有对象都包含 ai_summary 字段
      // 使用展开运算符创建新对象，确保所有字段都被保留
      const result = arr.map((p) => {
        // 从原始 results 中查找完整对象，确保不丢失任何字段
        // 使用多种方式匹配，确保能找到对应的论文
        let original = state.results.find(r => {
          // 优先使用ID匹配
          if (r.id === p.id) return true
          // 尝试字符串匹配
          if (String(r.id) === String(p.id)) return true
          // 尝试数字匹配
          if (Number(r.id) === Number(p.id)) return true
          return false
        })
        
        // 如果通过ID找不到，尝试使用标题匹配
        if (!original && p.title) {
          original = state.results.find(r => {
            return r.title && p.title && r.title.trim() === p.title.trim()
          })
          if (original) {
            console.warn(`⚠️ 论文 ${p.id} 在 filtered 中通过标题匹配到原始论文 ${original.id}`)
          }
        }
        
        if (original) {
          // 合并原始对象和当前对象，确保所有字段都被保留
          // 重要：使用原始对象的ID，确保与数据库中的ID一致
          return { ...original, ...p, id: original.id }
        }
        
        // 如果找不到原始对象，至少确保 ai_summary 字段存在
        if (!('ai_summary' in p)) {
          console.warn(`⚠️ 论文 ${p.id} 在 filtered 中缺少 ai_summary 字段，且找不到原始对象`)
          p.ai_summary = null
        }
        return { ...p }  // 创建新对象副本
      })
      
      // 调试：检查前10篇论文的推荐原因
      if (result.length > 0) {
        const first10 = result.slice(0, 10)
        const withSummary = first10.filter(p => p.ai_summary && p.ai_summary.trim())
        if (withSummary.length < first10.length) {
          console.warn(`⚠️ filtered 前10篇论文中，只有 ${withSummary.length} 篇有推荐原因`)
          first10.forEach((p, i) => {
            if (!p.ai_summary || !p.ai_summary.trim()) {
              console.warn(`  [${i+1}] 论文 ${p.id} 缺少推荐原因`)
            }
          })
        }
      }
      
      return result
    },
    pageItems() {
      const start = (this.page - 1) * this.pageSize
      const items = this.filtered.slice(start, start + this.pageSize)
      
      // 调试：检查当前页论文的推荐原因
      if (items.length > 0) {
        console.log(`=== pageItems 当前页 ${this.page} 的论文 ===`)
        items.forEach((p, i) => {
          const hasSummary = !!(p.ai_summary && p.ai_summary.trim())
          console.log(`  [${i+1}] ID: ${p.id}, 标题: ${p.title?.substring(0, 30)}..., 有推荐原因: ${hasSummary}`)
        })
      }
      
      return items
    },
    totalPages() {
      return Math.max(1, Math.ceil(this.filtered.length / this.pageSize))
    }
  },
  actions: {
    async doSearch(query, yearStart, yearEnd, userId = '') {
      if (!query) return
      this.lastQuery = query
      this.currentQuery = query // 保存当前查询，用于生成推荐原因
      try {
        const payload = {
          user_id: userId,
          question: query,
          year_start: yearStart,
          year_end: yearEnd,
          top_k: 100,
          page: 1,  // 第一页
          page_size: this.pageSize
        }
        const response = await search(payload)
        // axios返回的响应结构是 {data: {...}, status: 200, ...}
        // 后端返回的是 {results: [...], time_taken: ...}
        const results = response?.data?.results || response?.data?.data?.results || []
        console.log('=== 前端接收搜索结果 ===')
        console.log('Search response status:', response?.status)
        console.log('Search results count:', results.length)
        
        // 详细检查前10篇论文的推荐原因
        const firstPageResults = results.slice(0, this.pageSize)
        console.log('=== 前10篇论文的推荐原因状态（前端接收后）===')
        firstPageResults.forEach((paper, index) => {
          const hasSummary = !!(paper.ai_summary)
          const summaryLen = paper.ai_summary ? paper.ai_summary.length : 0
          const summaryTrimmed = paper.ai_summary ? paper.ai_summary.trim() : ''
          const hasValidSummary = !!(summaryTrimmed)
          
          console.log(`  [${index + 1}] Paper ID: ${paper.id}`)
          console.log(`      有ai_summary字段: ${hasSummary}`)
          console.log(`      字段长度: ${summaryLen}`)
          console.log(`      去除空格后长度: ${summaryTrimmed.length}`)
          console.log(`      有效推荐原因: ${hasValidSummary}`)
          if (hasSummary) {
            console.log(`      预览: ${paper.ai_summary.substring(0, 50)}...`)
          } else {
            console.log(`      ⚠️ 缺少推荐原因！字段值:`, paper.ai_summary)
          }
        })
        console.log('=== 检查完成 ===')
        
        const withSummary = firstPageResults.filter(p => p.ai_summary && p.ai_summary.trim())
        console.log(`前 ${this.pageSize} 篇论文中有 ${withSummary.length} 篇有推荐原因`)
        if (withSummary.length < firstPageResults.length) {
          const missing = firstPageResults.filter(p => !p.ai_summary || !p.ai_summary.trim())
          console.log('缺少推荐原因的论文:', missing.map(p => ({ 
            id: p.id, 
            title: p.title?.substring(0, 50),
            ai_summary: p.ai_summary,
            ai_summary_type: typeof p.ai_summary
          })))
        }
        
        // 在设置结果前，先检查并打印前10篇论文的ID和推荐原因
        console.log('=== 设置 results 前的检查 ===')
        const first10BeforeSet = results.slice(0, 10)
        first10BeforeSet.forEach((p, i) => {
          console.log(`  [${i+1}] ID: ${p.id}, 有推荐原因: ${!!p.ai_summary}, 长度: ${p.ai_summary?.length || 0}`)
        })
        
        // 调试：检查接收到的结果中的ID格式
        console.log('=== 设置 results 前的ID检查 ===')
        if (results.length > 0) {
          console.log('前10篇论文的ID:', results.slice(0, 10).map(r => ({ id: r.id, idType: typeof r.id, title: r.title?.substring(0, 30) })))
        }
        
        this.results = results
        this.page = 1
        
        // 设置后立即检查 filtered 和 pageItems
        await this.$nextTick?.() || new Promise(resolve => setTimeout(resolve, 100))
        console.log('=== 设置 results 后的检查 ===')
        console.log('filtered 长度:', this.filtered.length)
        console.log('pageItems 长度:', this.pageItems.length)
        const first10AfterFilter = this.filtered.slice(0, 10)
        const currentPageItems = this.pageItems
        console.log('=== filtered 前10篇论文 ===')
        first10AfterFilter.forEach((p, i) => {
          console.log(`  [${i+1}] ID: ${p.id}, 有推荐原因: ${!!p.ai_summary}, 长度: ${p.ai_summary?.length || 0}`)
        })
        console.log('=== pageItems 当前页论文 ===')
        currentPageItems.forEach((p, i) => {
          console.log(`  [${i+1}] ID: ${p.id}, 有推荐原因: ${!!p.ai_summary}, 长度: ${p.ai_summary?.length || 0}`)
        })
        // 如果没有结果，不抛出错误，只是返回空数组
        if (results.length === 0) {
          console.warn('No search results found')
        }
      } catch (error) {
        console.error('Search error:', error)
        console.error('Error details:', error?.response || error)
        this.results = []
        throw error
      }
    },
    async generatePageSummaries() {
      // 为当前页的论文生成推荐原因（使用并行处理加快速度）
      if (!this.currentQuery) {
        console.log('No current query, skipping summary generation')
        return
      }
      
      // 如果正在生成，跳过本次请求（避免重复请求）
      if (this.generatingSummaries) {
        console.log('[翻页] 正在生成推荐原因，跳过重复请求')
        return
      }
      
      // 关键修复：直接从原始 results 中获取当前页的论文，而不是从 filtered
      // 这样可以确保ID正确，避免 filtered 中的ID不匹配问题
      const filtered = this.filtered
      const start = (this.page - 1) * this.pageSize
      const currentPageItems = filtered.slice(start, start + this.pageSize)
      
      console.log(`[翻页] 正在为第 ${this.page} 页的 ${currentPageItems.length} 篇论文生成推荐原因...`)
      
      // 调试：打印当前页论文信息
      console.log(`[翻页] 调试：当前页论文（前3个）:`, currentPageItems.slice(0, 3).map(p => ({
        id: p.id,
        title: p.title?.substring(0, 30),
        hasSummary: !!(p.ai_summary && p.ai_summary.trim())
      })))
      
      const papersWithoutSummary = currentPageItems.filter(p => !p.ai_summary || !p.ai_summary.trim())
      
      if (papersWithoutSummary.length === 0) {
        console.log(`[翻页] 第 ${this.page} 页的所有论文已有推荐原因，跳过生成`)
        // 确保清除加载状态
        this.loadingPaperIds = []
        return
      }
      
      // 立即标记这些论文正在加载，显示加载状态
      // 使用数组并重新赋值，确保Vue能追踪到变化
      // 先清空之前的加载状态，再设置新的
      this.loadingPaperIds = papersWithoutSummary.map(p => p.id)
      
      // 使用 nextTick 确保加载状态已经更新到DOM
      await this.$nextTick?.() || new Promise(resolve => setTimeout(resolve, 0))
      
      console.log(`[翻页] 发现 ${papersWithoutSummary.length} 篇论文缺少推荐原因，开始批量生成（并行处理）...`)
      
      // 关键修复：优先使用标题匹配找到正确的ID
      // 因为 filtered 中的ID可能不正确，但标题应该是准确的
      const paperIds = papersWithoutSummary.map((p, index) => {
        // 优先使用标题匹配（更可靠）
        if (p.title) {
          const pTitle = p.title.trim()
          
          // 首先尝试完全匹配
          let titleMatch = this.results.find(r => {
            if (!r.title) return false
            return r.title.trim() === pTitle
          })
          
          // 如果完全匹配失败，尝试部分匹配（前40个字符）
          if (!titleMatch) {
            const pTitlePrefix = pTitle.substring(0, 40)
            titleMatch = this.results.find(r => {
              if (!r.title) return false
              return r.title.trim().substring(0, 40) === pTitlePrefix
            })
            if (titleMatch) {
              console.log(`[翻页] ⚠️ 论文 ${index + 1} 通过部分标题匹配（前40字符）找到，ID: ${p.id} -> ${titleMatch.id}`)
            }
          }
          
          if (titleMatch) {
            if (titleMatch.id !== p.id) {
              console.log(`[翻页] ✅ 论文 ${index + 1} "${p.title.substring(0, 40)}" 通过标题匹配，ID: ${p.id} -> ${titleMatch.id}`)
            }
            return titleMatch.id
          } else {
            // 标题匹配失败，记录详细信息
            console.error(`[翻页] ❌ 论文 ${index + 1} 标题匹配失败:`)
            console.error(`  - filtered中的ID: ${p.id}`)
            console.error(`  - 标题: ${p.title?.substring(0, 50)}`)
            console.error(`  - 原始results中是否有相似标题:`)
            // 检查原始results中是否有相似的标题
            const similarTitles = this.results.filter(r => {
              if (!r.title || !p.title) return false
              return r.title.toLowerCase().includes(p.title.toLowerCase().substring(0, 20)) || 
                     p.title.toLowerCase().includes(r.title.toLowerCase().substring(0, 20))
            }).slice(0, 3)
            if (similarTitles.length > 0) {
              console.error(`  - 找到相似标题:`, similarTitles.map(r => ({ id: r.id, title: r.title?.substring(0, 40) })))
            }
          }
        }
        
        // 如果标题匹配失败，尝试ID匹配
        const idMatch = this.results.find(r => {
          if (r.id === p.id) return true
          if (String(r.id) === String(p.id)) return true
          if (Number(r.id) === Number(p.id)) return true
          return false
        })
        
        if (idMatch) {
          return idMatch.id
        }
        
        // 如果都找不到，返回当前ID，让后端尝试查找（虽然可能找不到）
        console.error(`[翻页] ❌ 论文 ${index + 1} 所有匹配方式都失败，使用原始ID: ${p.id}`)
        return p.id
      })
      
      // 调试：打印将要发送的ID和原始 results 中的ID对比
      console.log(`[翻页] 调试：将要发送的ID列表（前5个）:`, paperIds.slice(0, 5))
      console.log(`[翻页] 调试：ID类型:`, paperIds.slice(0, 5).map(id => typeof id))
      console.log(`[翻页] 调试：原始 results 中的ID（前5个）:`, this.results.slice(0, 5).map(r => r.id))
      console.log(`[翻页] 调试：原始 results 中的ID类型:`, this.results.slice(0, 5).map(r => typeof r.id))
      
      // 收集标题列表，用于后端通过标题匹配找到论文
      const paperTitles = papersWithoutSummary.map(p => {
        const title = p.title || ''
        if (!title) {
          console.warn(`[翻页] ⚠️ 论文 ID ${p.id} 没有标题，将使用空字符串`)
        }
        return title
      })
      
      // 确保标题列表不为空（即使标题为空字符串，也要传递数组）
      console.log(`[翻页] 🔍 收集到的标题列表: 长度=${paperTitles.length}, 前3个=`, paperTitles.slice(0, 3))
      console.log(`[翻页] 🔍 标题列表类型: ${Array.isArray(paperTitles) ? 'Array' : typeof paperTitles}`)
      
      // 设置生成状态
      this.generatingSummaries = true
      
      try {
        console.log(`[翻页] 调用批量生成接口，paperIds: ${paperIds.length} 个`, paperIds)
        console.log(`[翻页] 传递标题列表: ${paperTitles.length} 个`, paperTitles.slice(0, 3))
        console.log(`[翻页] 标题列表详情（前3个）:`, paperTitles.slice(0, 3).map((t, i) => ({ index: i, title: t, length: t.length })))
        console.log(`[翻页] 🔍 准备发送的请求数据:`, {
          paper_ids: paperIds.slice(0, 3),
          user_query: this.currentQuery?.substring(0, 30),
          paper_titles: paperTitles.slice(0, 3),
          paper_titles_type: Array.isArray(paperTitles) ? 'Array' : typeof paperTitles
        })
        const response = await batchGenerateSummary(paperIds, this.currentQuery, paperTitles)
        console.log('批量生成接口响应:', response)
        console.log('响应数据结构:', {
          hasData: !!response?.data,
          hasResults: !!response?.data?.results,
          resultsType: typeof response?.data?.results,
          resultsKeys: response?.data?.results ? Object.keys(response?.data?.results) : []
        })
        
        const summaries = response?.data?.results || response?.data?.data?.results || {}
        
        console.log(`Received summaries for ${Object.keys(summaries).length} papers`)
        console.log('Summaries 内容:', summaries)
        
        // 检查哪些论文有推荐原因
        const papersWithSummary = Object.keys(summaries).filter(id => summaries[id] && summaries[id].trim())
        console.log(`有效的推荐原因数量: ${papersWithSummary.length}`)
        console.log('所有 summaries 的键值对:', Object.entries(summaries).slice(0, 5).map(([k, v]) => ({
          key: k,
          keyType: typeof k,
          value: v ? v.substring(0, 50) : v,
          valueType: typeof v,
          hasValue: !!v
        })))
        
        papersWithSummary.forEach(id => {
          console.log(`  ✅ Paper ${id} (类型: ${typeof id}): 长度 ${summaries[id].length}`)
        })
        
        // 更新结果中的推荐原因
        // 注意：paper.id 可能是字符串或数字，需要确保类型匹配
        let updatedCount = 0
        let matchedIds = []
        let unmatchedIds = []
        
        this.results = this.results.map(paper => {
          const paperId = paper.id
          const paperIdType = typeof paperId
          
          // 尝试多种方式匹配ID（字符串、数字）
          let summary = summaries[paperId]
          let matchedKey = paperId
          
          if (!summary) {
            // 尝试字符串匹配
            const strId = String(paperId)
            if (summaries[strId]) {
              summary = summaries[strId]
              matchedKey = strId
            }
          }
          if (!summary) {
            // 尝试数字匹配
            const numId = Number(paperId)
            if (!isNaN(numId) && summaries[numId]) {
              summary = summaries[numId]
              matchedKey = numId
            }
          }
          
          // 如果还是没找到，尝试遍历所有键进行匹配
          if (!summary) {
            for (const [key, value] of Object.entries(summaries)) {
              if (String(key) === String(paperId) || Number(key) === Number(paperId)) {
                summary = value
                matchedKey = key
                break
              }
            }
          }
          
          if (summary && summary.trim()) {
            updatedCount++
            matchedIds.push({ paperId, paperIdType, matchedKey, matchedKeyType: typeof matchedKey })
            console.log(`  ✅ 更新论文 ${paperId} (${paperIdType}) 的推荐原因，匹配键: ${matchedKey} (${typeof matchedKey})，长度: ${summary.length}`)
            return { ...paper, ai_summary: summary.trim() }
          } else {
            unmatchedIds.push({ paperId, paperIdType, availableKeys: Object.keys(summaries).slice(0, 3) })
            return paper
          }
        })
        
        console.log(`Summaries updated in results: ${updatedCount} 篇论文已更新`)
        
        // 验证更新后的结果
        if (updatedCount > 0) {
          const updatedPapers = this.results.filter(p => {
            const paperId = p.id
            return paperIds.includes(paperId) && p.ai_summary && p.ai_summary.trim()
          })
          console.log(`验证：更新后，${updatedPapers.length} 篇论文有推荐原因`)
          updatedPapers.slice(0, 3).forEach(p => {
            console.log(`  ✅ 论文 ${p.id}: ${p.ai_summary.substring(0, 50)}...`)
          })
        } else {
          console.warn('⚠️ 没有更新任何论文的推荐原因！')
          console.warn('未匹配的论文ID:', unmatchedIds.slice(0, 5))
          console.warn('可用的 summaries 键:', Object.keys(summaries).slice(0, 10))
          console.warn('请求的 paperIds:', paperIds.slice(0, 5))
        }
        
        // 清除加载状态
        this.loadingPaperIds = []
        
        // 强制触发响应式更新
        // 通过重新赋值整个数组来确保 Vue 检测到变化
        this.results = [...this.results]
        console.log(`[翻页] ✅ 第 ${this.page} 页的推荐原因生成完成`)
      } catch (error) {
        // 清除加载状态（即使出错也要清除）
        this.loadingPaperIds = []
        
        console.error('[翻页] ❌ 生成推荐原因时出错:', error)
        console.error('Error details:', error?.response || error)
        if (error?.response) {
          console.error('Error response data:', error.response.data)
          console.error('Error response status:', error.response.status)
        }
      } finally {
        // 重置生成状态
        this.generatingSummaries = false
        // 确保清除所有加载状态
        this.loadingPaperIds = []
      }
    },
    async startProgressiveSummaryGeneration() {
      // 渐进式生成推荐原因：优先生成当前页可见的论文，然后生成其他论文
      console.log('startProgressiveSummaryGeneration 被调用')
      console.log('currentQuery:', this.currentQuery)
      console.log('results count:', this.results.length)
      
      if (!this.currentQuery) {
        console.log('No current query, skipping progressive summary generation')
        return
      }
      
      // 获取当前页的论文（优先生成）
      const filtered = this.filtered
      console.log('filtered count:', filtered.length)
      
      if (!filtered || filtered.length === 0) {
        console.log('No filtered results, using raw results')
        // 如果没有过滤结果，使用原始结果
        const allPapers = this.results || []
        if (allPapers.length === 0) {
          console.log('No results to generate summaries for')
          return
        }
        
        // 直接为所有论文生成推荐原因
        const papersToGenerate = allPapers.filter(p => {
          return !p.ai_summary || !p.ai_summary.trim()
        })
        
        if (papersToGenerate.length === 0) {
          console.log('All papers already have summaries')
          return
        }
        
        console.log(`开始渐进式生成推荐原因，共 ${papersToGenerate.length} 篇论文`)
        
        // 逐个生成
        for (let i = 0; i < papersToGenerate.length; i++) {
          const paper = papersToGenerate[i]
          
          const currentPaper = this.results.find(p => p.id === paper.id)
          if (!currentPaper) {
            console.log(`Paper ${paper.id} no longer in results, skipping`)
            continue
          }
          
          if (currentPaper.ai_summary && currentPaper.ai_summary.trim()) {
            console.log(`Paper ${paper.id} already has summary, skipping`)
            continue
          }
          
          try {
            console.log(`正在为第 ${i + 1}/${papersToGenerate.length} 篇论文生成推荐原因: ${paper.id}`)
            console.log(`查询内容: ${this.currentQuery}`)
            
            const response = await generateSingleSummary(paper.id, this.currentQuery)
            console.log(`收到响应:`, response)
            
            const summary = response?.data?.summary || response?.data?.data?.summary
            console.log(`生成的摘要:`, summary ? summary.substring(0, 50) + '...' : 'null')
            
            if (summary && summary.trim() && !summary.includes('生成失败')) {
              const paperIndex = this.results.findIndex(p => p.id === paper.id)
              if (paperIndex !== -1) {
                // 使用 Vue 的响应式更新方式
                this.results[paperIndex] = { ...this.results[paperIndex], ai_summary: summary }
                // 触发响应式更新
                this.results = [...this.results]
                console.log(`✅ 已为论文 ${paper.id} 生成推荐原因`)
              } else {
                console.warn(`⚠️ 论文 ${paper.id} 不在结果列表中`)
              }
            } else {
              console.warn(`⚠️ 论文 ${paper.id} 生成推荐原因失败或为空:`, summary)
            }
          } catch (error) {
            console.error(`❌ 为论文 ${paper.id} 生成推荐原因时出错:`, error)
            console.error('错误详情:', error.response || error.message)
          }
          
          if (i < papersToGenerate.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 100))
          }
        }
        
        console.log('渐进式生成推荐原因完成')
        return
      }
      
      const start = (this.page - 1) * this.pageSize
      const currentPageItems = filtered.slice(start, start + this.pageSize)
      
      // 获取所有需要生成推荐原因的论文
      const allPapers = filtered || this.results
      const allPapersToGenerate = allPapers.filter(p => {
        const resultPaper = this.results.find(r => r.id === p.id)
        return resultPaper && (!resultPaper.ai_summary || !resultPaper.ai_summary.trim())
      })
      
      if (allPapersToGenerate.length === 0) {
        console.log('All papers already have summaries')
        return
      }
      
      // 分离当前页和其他页的论文
      const currentPageIds = new Set(currentPageItems.map(p => p.id))
      const currentPageToGenerate = allPapersToGenerate.filter(p => currentPageIds.has(p.id))
      const otherPagesToGenerate = allPapersToGenerate.filter(p => !currentPageIds.has(p.id))
      
      // 合并：先当前页，后其他页
      const papersToGenerate = [...currentPageToGenerate, ...otherPagesToGenerate]
      
      console.log(`开始渐进式生成推荐原因，共 ${papersToGenerate.length} 篇论文（当前页: ${currentPageToGenerate.length}）`)
      
      // 逐个生成，生成一个就更新一个
      for (let i = 0; i < papersToGenerate.length; i++) {
        const paper = papersToGenerate[i]
        
        // 检查论文是否还在结果中（用户可能已经切换页面或搜索）
        const currentPaper = this.results.find(p => p.id === paper.id)
        if (!currentPaper) {
          console.log(`Paper ${paper.id} no longer in results, skipping`)
          continue
        }
        
        // 如果已经有推荐原因了，跳过
        if (currentPaper.ai_summary && currentPaper.ai_summary.trim()) {
          console.log(`Paper ${paper.id} already has summary, skipping`)
          continue
        }
        
        try {
          const isCurrentPage = currentPageIds.has(paper.id)
          console.log(`正在为第 ${i + 1}/${papersToGenerate.length} 篇论文生成推荐原因: ${paper.id} ${isCurrentPage ? '(当前页)' : ''}`)
          
          const response = await generateSingleSummary(paper.id, this.currentQuery)
          const summary = response?.data?.summary || response?.data?.data?.summary
          
          if (summary && summary.trim() && !summary.includes('生成失败')) {
            // 更新结果中的推荐原因
            const paperIndex = this.results.findIndex(p => p.id === paper.id)
            if (paperIndex !== -1) {
              this.results[paperIndex] = { ...this.results[paperIndex], ai_summary: summary }
              console.log(`✅ 已为论文 ${paper.id} 生成推荐原因`)
            }
          } else {
            console.warn(`⚠️ 论文 ${paper.id} 生成推荐原因失败或为空`)
          }
        } catch (error) {
          console.error(`❌ 为论文 ${paper.id} 生成推荐原因时出错:`, error)
          // 继续生成下一篇，不中断
        }
        
        // 添加小延迟，避免请求过于频繁（当前页延迟更短）
        const delay = currentPageIds.has(paper.id) ? 50 : 100
        if (i < papersToGenerate.length - 1) {
          await new Promise(resolve => setTimeout(resolve, delay))
        }
      }
      
      console.log('渐进式生成推荐原因完成')
    }
  }
})




