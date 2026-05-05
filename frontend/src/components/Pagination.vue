<template>
  <div class="pg">
    <el-pagination
      layout="prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="$emit('change', $event)"
    />
  </div>
</template>

<script setup>
defineProps({
  total: Number,
  page: Number,
  pageSize: Number
})
defineEmits(['change'])
</script>

<style scoped>
.pg {
  display: flex;
  justify-content: center;
  margin: 8px 0;
}
</style>





