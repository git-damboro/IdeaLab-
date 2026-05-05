<template>
  <el-card>
    <el-select v-model="sort" placeholder="排序" class="mb8">
      <el-option label="相关性" value="相关性" />
      <el-option label="年份: 新→旧" value="年份: 新→旧" />
      <el-option label="年份: 旧→新" value="年份: 旧→新" />
    </el-select>
    <el-slider v-model="years" range :min="2000" :max="2030" class="mb8" />
    <el-select v-model="months" multiple placeholder="月份(可选)" class="mb8">
      <el-option v-for="m in allMonths" :key="m" :label="m" :value="m" />
    </el-select>
    <el-button type="primary" @click="emitChange" block>确定</el-button>
  </el-card>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  allMonths: Array,
  init: Object
})
const emit = defineEmits(['change'])

const sort = ref(props.init?.sort ?? '相关性')
const years = ref(props.init?.years ?? [2018, 2025])
const months = ref(props.init?.months ?? [])
const allMonths = computed(() => props.allMonths || [])

const emitChange = () => emit('change', { sort: sort.value, years: years.value, months: months.value })
</script>

<style scoped>
.mb8 {
  margin-bottom: 8px;
  width: 100%;
}
</style>





