<template>
  <div class="bar">
    <el-input v-model="q" placeholder="输入研究课题..." @keyup.enter="emitSearch" />
    <div class="year">
      <span>年份</span>
      <el-slider v-model="years" range :min="2000" :max="2030" />
    </div>
    <el-button type="primary" @click="emitSearch">搜索</el-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['search'])
const q = ref('')
const years = ref([2018, 2025])

const emitSearch = () => {
  emit('search', q.value, years.value)
}
</script>

<style scoped>
.bar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.year {
  width: 260px;
}
</style>





