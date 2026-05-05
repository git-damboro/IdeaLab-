<template>
  <div>
    <div class="page-head">
      <h2>用户与角色</h2>
      <div class="actions">
        <el-input v-model="keyword" placeholder="搜索用户名" clearable @keyup.enter="loadUsers" />
        <el-button type="primary" @click="loadUsers">搜索</el-button>
      </div>
    </div>

    <el-table :data="rows" border v-loading="loading">
      <el-table-column prop="username" label="用户名" width="220" />
      <el-table-column label="角色" min-width="380">
        <template #default="{ row }">
          <el-select
            v-model="row.role_codes"
            multiple
            collapse-tags
            collapse-tags-tooltip
            style="width: 100%"
            @change="(val) => saveRoles(row.username, val)"
          >
            <el-option v-for="r in roles" :key="r.code" :label="`${r.name} (${r.code})`" :value="r.code" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" min-width="220" />
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
import { listAdminRoles, listAdminUsers, updateAdminUserRoles } from "../services/api";

const loading = ref(false);
const rows = ref([]);
const roles = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const keyword = ref("");

const loadRoles = async () => {
  const data = await listAdminRoles();
  roles.value = data.items || [];
};

const loadUsers = async () => {
  loading.value = true;
  try {
    const data = await listAdminUsers({ page: page.value, pageSize: pageSize.value, keyword: keyword.value });
    rows.value = (data.items || []).map((u) => ({ ...u }));
    total.value = data.total || 0;
  } catch (e) {
    ElMessage.error(e.detail || "加载用户失败");
  } finally {
    loading.value = false;
  }
};

const saveRoles = async (username, roleCodes) => {
  try {
    await updateAdminUserRoles(username, roleCodes);
    ElMessage.success(`已更新 ${username} 的角色`);
  } catch (e) {
    ElMessage.error(e.detail || "更新角色失败");
    await loadUsers();
  }
};

const onPageChange = async (p) => {
  page.value = p;
  await loadUsers();
};

onMounted(async () => {
  await loadRoles();
  await loadUsers();
});
</script>
