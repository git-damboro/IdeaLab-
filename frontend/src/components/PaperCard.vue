<template>
  <el-card class="card" shadow="hover">
    <div class="title">
      <a :href="paper.url" target="_blank">{{ paper.title }}</a>
      <span class="score">匹配度 {{ formatScore(paper.score) }}%</span>
    </div>
    <div class="meta">
      <el-tag size="small">{{ paper.year }}</el-tag>
      <span>{{ paper.month }}</span>
    </div>
    <!-- 加载状态 -->
    <div v-if="isLoading" class="ai ai-loading">
      <el-tag type="info" size="small">AI 导读</el-tag>
      <div class="loading-placeholder">
        <span class="loading-dots">
          <span></span><span></span><span></span>
        </span>
        <span class="loading-text">正在生成推荐原因...</span>
      </div>
    </div>
    <!-- 推荐原因内容（带平滑过渡） -->
    <transition name="fade">
      <div v-if="paper.ai_summary && !isLoading" class="ai">
      <el-tag type="success" size="small">AI 导读</el-tag>
      <span class="ai-text">{{ paper.ai_summary }}</span>
    </div>
    </transition>
    <div class="abs">Abstract: {{ (paper.abstract || '').slice(0, 200) }}...</div>
    <el-button size="small" :type="paper.is_favorited ? 'danger' : 'primary'" @click="$emit('toggle')">
      {{ paper.is_favorited ? '已收藏' : '收藏' }}
    </el-button>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useSearchStore } from '../store/search'

const props = defineProps({ paper: Object })

const searchStore = useSearchStore()

// 计算是否正在加载
const isLoading = computed(() => {
  return searchStore.loadingPaperIds.includes(props.paper.id)
})

// 格式化匹配度分数显示
const formatScore = (score) => {
  if (score === null || score === undefined) return '0.0'
  const num = typeof score === 'string' ? parseFloat(score) : score
  if (isNaN(num)) return '0.0'
  return num.toFixed(1)
}
</script>

<style scoped>
.card {
  margin-bottom: 10px;
}
.title {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.meta {
  display: flex;
  gap: 8px;
  margin: 6px 0;
  color: #666;
}
.ai {
  background: #f0fdf4;
  padding: 6px;
  border: 1px solid #bbf7d0;
  border-radius: 4px;
  margin-bottom: 6px;
  display: flex;
  gap: 6px;
  transition: all 0.3s ease;
}

.ai-loading {
  background: #f9fafb;
  border-color: #e5e7eb;
}

.loading-placeholder {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 13px;
}

.loading-dots {
  display: inline-flex;
  gap: 4px;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
  animation: loading-bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes loading-bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.loading-text {
  font-size: 13px;
  color: #6b7280;
}

/* 平滑过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(-5px);
}

.fade-enter-to {
  opacity: 1;
  transform: translateY(0);
}

.fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}
.abs {
  color: #555;
  margin: 6px 0;
}
.score {
  color: #999;
  font-size: 12px;
  white-space: nowrap;
}
</style>





