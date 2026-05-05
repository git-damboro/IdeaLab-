<template>
  <div>
    <div class="page-head">
      <h2>审计日志</h2>
      <div class="actions"><el-button type="primary" @click="loadLogs">刷新</el-button></div>
    </div>

    <el-table :data="rows" border v-loading="loading">
      <el-table-column prop="created_at" label="时间" min-width="200" />
      <el-table-column prop="actor" label="操作人" width="140" />
      <el-table-column label="动作" width="160">
        <template #default="{ row }">{{ mapAction(row.action) }}</template>
      </el-table-column>
      <el-table-column label="资源" width="120">
        <template #default="{ row }">{{ mapResource(row.resource) }}</template>
      </el-table-column>
      <el-table-column prop="resource_id" label="资源ID" min-width="180" />
      <el-table-column label="详情" min-width="260">
        <template #default="{ row }"><code>{{ JSON.stringify(row.detail || {}) }}</code></template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        layout="prev, pager, next, total"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { listAdminAuditLogs } from "../services/api";

const loading = ref(false);
const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);

const mapAction = (action) => {
  const map = {
    create: "创建",
    update: "更新",
    publish: "发布",
    offline: "下架",
    retry: "重试任务",
    workflow_transition: "流程流转",
    update_roles: "更新角色",
    update_permissions: "更新权限",
    update_status: "更新状态"
  };
  return map[action] || action || "-";
};

const mapResource = (resource) => {
  const map = { paper: "论文", user: "用户", job: "任务", role: "角色" };
  return map[resource] || resource || "-";
};

const loadLogs = async () => {
  loading.value = true;
  try {
    const data = await listAdminAuditLogs({ page: page.value, pageSize: pageSize.value });
    rows.value = data.items || [];
    total.value = data.total || 0;
  } catch (e) {
    ElMessage.error(e.detail || "加载审计日志失败");
  } finally {
    loading.value = false;
  }
};

const onPageChange = async (p) => {
  page.value = p;
  await loadLogs();
};

onMounted(loadLogs);
</script>
