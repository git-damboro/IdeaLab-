<template>
  <div class="layout">
    <div class="left">
      <SearchBar @search="onSearch" />
      <FilterPanel :all-months="allMonths" :init="search.filters" @change="onFilter" />
      <div v-if="pageItems.length === 0" class="empty">无结果</div>
      <PaperCard
        v-for="p in pageItems"
        :key="p.id"
        :paper="p"
        @toggle="() => toggleFav(p)"
      />
      <Pagination
        :total="filtered.length"
        :page="search.page"
        :page-size="search.pageSize"
        @change="onPage"
      />
    </div>
    <div class="right">
      <ChatPanel :context="pageItems" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useSearchStore } from '../store/search'
import { useFavStore } from '../store/fav'
import { useAuthStore } from '../store/auth'
import SearchBar from '../components/SearchBar.vue'
import PaperCard from '../components/PaperCard.vue'
import FilterPanel from '../components/FilterPanel.vue'
import Pagination from '../components/Pagination.vue'
import ChatPanel from '../components/ChatPanel.vue'

const search = useSearchStore()
const fav = useFavStore()
const auth = useAuthStore()
const router = useRouter()

const { filtered, pageItems } = storeToRefs(search)
const allMonths = computed(() => {
  const months = new Set((search.results || []).map((p) => p.month).filter(Boolean))
  return Array.from(months).sort()
})

const onSearch = (q, yr) => search.doSearch(q, yr[0], yr[1], auth.userId)
const onFilter = (payload) => {
  search.filters = payload
  search.page = 1
}
const onPage = async (p) => {
  // 先更新页码
  search.page = p
  
  // 立即检查当前页是否需要生成推荐原因，并设置加载状态
  if (search.currentQuery && search.results.length > 0) {
    // 使用 nextTick 确保页面先渲染
    await new Promise(resolve => setTimeout(resolve, 0))
    
    // 检查当前页的论文是否需要生成推荐原因
    const filtered = search.filtered
    const start = (p - 1) * search.pageSize
    const currentPageItems = filtered.slice(start, start + search.pageSize)
    const papersWithoutSummary = currentPageItems.filter(p => !p.ai_summary || !p.ai_summary.trim())
    
    // 如果有需要生成的论文，立即设置加载状态
    if (papersWithoutSummary.length > 0) {
      search.loadingPaperIds = papersWithoutSummary.map(paper => paper.id)
    }
    
    // 然后生成推荐原因
    await search.generatePageSummaries()
  }
}
const toggleFav = (paper) => {
  if (!auth.userId) {
    router.push('/login')
    return
  }
  fav.toggle(auth.userId, paper)
}

onMounted(() => {
  if (!auth.userId) {
    router.push('/login')
  } else {
    fav.load(auth.userId)
  }
})
</script>

<style scoped>
.layout {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  box-sizing: border-box;
}
.left {
  flex: 2;
  overflow: auto;
}
.right {
  flex: 1;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 8px;
  overflow: auto;
}
.empty {
  padding: 16px;
  color: #888;
}
</style>





