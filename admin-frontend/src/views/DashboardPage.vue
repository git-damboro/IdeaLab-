<template>
  <div>
    <div class="page-head">
      <h2>仪表盘</h2>
      <div class="actions">
        <el-select v-model="days" style="width: 120px" @change="loadTrend">
          <el-option :value="7" label="近7天" />
          <el-option :value="14" label="近14天" />
          <el-option :value="30" label="近30天" />
        </el-select>
        <el-button type="primary" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="6">
        <el-card><div class="metric">论文总数</div><div class="metric-value">{{ stats.totalPapers }}</div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card><div class="metric">已发布论文</div><div class="metric-value">{{ stats.publishedPapers }}</div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card><div class="metric">用户总数</div><div class="metric-value">{{ stats.totalUsers }}</div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card><div class="metric">待处理任务</div><div class="metric-value">{{ stats.pendingJobs }}</div></el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="8">
        <el-card><div class="metric">24h 新任务</div><div class="metric-value">{{ stats.newJobs24h }}</div></el-card>
      </el-col>
      <el-col :span="8">
        <el-card><div class="metric">24h 成功任务</div><div class="metric-value">{{ stats.successJobs24h }}</div></el-card>
      </el-col>
      <el-col :span="8">
        <el-card><div class="metric">24h 成功率</div><div class="metric-value">{{ stats.successRate24h }}%</div></el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 16px">
      <template #header>趋势数据</template>
      <el-table :data="trendRows" border>
        <el-table-column prop="date" label="日期" width="140" />
        <el-table-column prop="new_papers" label="新增论文" />
        <el-table-column prop="new_users" label="新增用户" />
        <el-table-column prop="new_jobs" label="新增任务" />
        <el-table-column prop="success_jobs" label="成功任务" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { getAdminOverview, getAdminTrend } from "../services/api";

const days = ref(7);
const trendRows = ref([]);

const stats = reactive({
  totalPapers: 0,
  publishedPapers: 0,
  totalUsers: 0,
  pendingJobs: 0,
  newJobs24h: 0,
  successJobs24h: 0,
  successRate24h: 0
});

const loadOverview = async () => {
  const data = await getAdminOverview();
  stats.totalPapers = data.total_papers || 0;
  stats.publishedPapers = data.published_papers || 0;
  stats.totalUsers = data.total_users || 0;
  stats.pendingJobs = data.pending_jobs || 0;
  stats.newJobs24h = data.new_jobs_24h || 0;
  stats.successJobs24h = data.success_jobs_24h || 0;
  stats.successRate24h = data.success_rate_24h || 0;
};

const loadTrend = async () => {
  const data = await getAdminTrend(days.value);
  trendRows.value = data.items || [];
};

const loadAll = async () => {
  try {
    await loadOverview();
    await loadTrend();
  } catch (e) {
    ElMessage.error(e.detail || "加载仪表盘失败");
  }
};

onMounted(loadAll);
</script>
