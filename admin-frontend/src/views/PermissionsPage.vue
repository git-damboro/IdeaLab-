<template>
  <div>
    <div class="page-head">
      <h2>权限矩阵</h2>
      <div class="actions"><el-button type="primary" @click="loadAll">刷新</el-button></div>
    </div>

    <el-table :data="rows" border v-loading="loading">
      <el-table-column prop="role_name" label="角色" width="220" />
      <el-table-column label="权限" min-width="560">
        <template #default="{ row }">
          <el-select
            v-model="row.permissions"
            multiple
            collapse-tags
            collapse-tags-tooltip
            style="width: 100%"
            @change="(val) => saveRolePerms(row.role_code, val)"
          >
            <el-option v-for="p in allPermissions" :key="p.code" :label="`${p.name} (${p.code})`" :value="p.code" />
          </el-select>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  listAdminPermissions,
  listAdminRolePermissions,
  listAdminRoles,
  updateAdminRolePermissions
} from "../services/api";

const loading = ref(false);
const rows = ref([]);
const allPermissions = ref([]);

const loadAll = async () => {
  loading.value = true;
  try {
    const [rolesData, permsData, mappingsData] = await Promise.all([
      listAdminRoles(),
      listAdminPermissions(),
      listAdminRolePermissions()
    ]);

    const mapping = {};
    for (const x of mappingsData.items || []) {
      mapping[x.role_code] = x.permissions || [];
    }

    allPermissions.value = permsData.items || [];
    rows.value = (rolesData.items || []).map((r) => ({
      role_code: r.code,
      role_name: `${r.name} (${r.code})`,
      permissions: [...(mapping[r.code] || [])]
    }));
  } catch (e) {
    ElMessage.error(e.detail || "加载权限矩阵失败");
  } finally {
    loading.value = false;
  }
};

const saveRolePerms = async (roleCode, permissions) => {
  try {
    await updateAdminRolePermissions(roleCode, permissions);
    ElMessage.success(`角色 ${roleCode} 权限已更新`);
  } catch (e) {
    ElMessage.error(e.detail || "更新权限失败");
    await loadAll();
  }
};

onMounted(loadAll);
</script>
