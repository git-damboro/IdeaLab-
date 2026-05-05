<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="brand">论文管理后台</div>
      <router-link to="/dashboard" class="nav-link">仪表盘</router-link>
      <router-link to="/papers" class="nav-link">论文管理</router-link>
      <router-link to="/users" class="nav-link">用户与角色</router-link>
      <router-link to="/permissions" class="nav-link">权限矩阵</router-link>
      <router-link to="/reviews" class="nav-link">审稿流程</router-link>
      <router-link to="/jobs" class="nav-link">任务中心</router-link>
      <router-link to="/audit-logs" class="nav-link">审计日志</router-link>
      <el-button @click="logout" class="logout-btn">退出登录</el-button>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();

const logout = () => {
  auth.logout();
  router.push("/login");
};
</script>
