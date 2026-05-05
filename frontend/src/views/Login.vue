<template>
  <div class="login">
    <el-card class="box">
      <el-tabs v-model="tab">
        <el-tab-pane label="登录" name="login">
          <el-form @submit.prevent="onLogin">
            <el-input v-model="u" placeholder="账号" />
            <el-input v-model="p" placeholder="密码" type="password" class="mt8" />
            <el-button type="primary" class="mt12" @click="onLogin" block>登录</el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form @submit.prevent="onRegister">
            <el-input v-model="u" placeholder="账号" />
            <el-input v-model="p" placeholder="密码" type="password" class="mt8" />
            <el-button class="mt12" @click="onRegister" block>注册</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const tab = ref('login')
const u = ref('')
const p = ref('')
const auth = useAuthStore()
const router = useRouter()

const onLogin = async () => {
  if (!u.value || !p.value) return
  await auth.doLogin(u.value, p.value)
  router.push('/')
}

const onRegister = async () => {
  if (!u.value || !p.value) return
  await auth.doRegister(u.value, p.value)
}

watch(
  () => auth.userId,
  (val) => {
    if (val) router.push('/')
  }
)
</script>

<style scoped>
.login {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: #f5f7fa;
}
.box {
  width: 360px;
}
.mt8 {
  margin-top: 8px;
}
.mt12 {
  margin-top: 12px;
}
</style>





