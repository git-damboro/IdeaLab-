<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2>管理端登录</h2>
      <el-form @submit.prevent="onSubmit">
        <el-form-item label="账号">
          <el-input v-model="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="onSubmit" class="full">登录</el-button>
      </el-form>
      <p class="hint">请使用管理员账号（用户名通常为 admin）。</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
const username = ref("");
const password = ref("");
const loading = ref(false);

const onSubmit = async () => {
  if (!username.value || !password.value) {
    ElMessage.warning("请输入账号和密码");
    return;
  }
  loading.value = true;
  try {
    await auth.login(username.value, password.value);
    router.push("/dashboard");
  } catch (e) {
    ElMessage.error(e.detail || "登录失败");
  } finally {
    loading.value = false;
  }
};
</script>
