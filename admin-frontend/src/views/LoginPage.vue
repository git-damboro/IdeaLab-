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
    <el-dialog
      v-model="passwordDialogVisible"
      title="首次登录请修改密码"
      width="420px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <el-form @submit.prevent="submitPasswordChange" label-position="top">
        <el-form-item label="当前密码">
          <el-input v-model="passwordForm.current" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.next" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirm" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" :loading="changingPassword" @click="submitPasswordChange">
          保存并进入后台
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
const username = ref("");
const password = ref("");
const loading = ref(false);
const passwordDialogVisible = ref(false);
const changingPassword = ref(false);
const passwordForm = ref({ current: "", next: "", confirm: "" });

const onSubmit = async () => {
  if (!username.value || !password.value) {
    ElMessage.warning("请输入账号和密码");
    return;
  }
  loading.value = true;
  try {
    await auth.login(username.value, password.value);
    if (auth.mustChangePassword) {
      passwordForm.value.current = password.value;
      passwordDialogVisible.value = true;
      return;
    }
    router.push("/dashboard");
  } catch (e) {
    ElMessage.error(e.detail || "登录失败");
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  if (auth.token && auth.mustChangePassword) {
    passwordDialogVisible.value = true;
  }
});

const submitPasswordChange = async () => {
  if (!passwordForm.value.current || !passwordForm.value.next || !passwordForm.value.confirm) {
    ElMessage.warning("请完整填写密码信息");
    return;
  }
  if (passwordForm.value.next.length < 6 || passwordForm.value.next.length > 16) {
    ElMessage.warning("密码长度必须为6到16位");
    return;
  }
  if (!/[a-zA-Z]/.test(passwordForm.value.next) || !/[0-9]/.test(passwordForm.value.next)) {
    ElMessage.warning("密码必须同时包含字母和数字");
    return;
  }
  if (!/^[a-zA-Z0-9]+$/.test(passwordForm.value.next)) {
    ElMessage.warning("密码只能包含字母和数字");
    return;
  }
  if (passwordForm.value.next !== passwordForm.value.confirm) {
    ElMessage.warning("两次输入的新密码不一致");
    return;
  }
  changingPassword.value = true;
  try {
    await auth.changePassword(passwordForm.value.current, passwordForm.value.next);
    ElMessage.success("密码已修改");
    passwordDialogVisible.value = false;
    passwordForm.value = { current: "", next: "", confirm: "" };
    password.value = "";
    router.push("/dashboard");
  } catch (e) {
    ElMessage.error(e.detail || "密码修改失败");
  } finally {
    changingPassword.value = false;
  }
};
</script>
