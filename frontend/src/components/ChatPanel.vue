<template>
  <div class="chat">
    <div class="history">
      <div v-for="(m, i) in chat.history" :key="i" :class="m.role">{{ m.role }}: {{ m.content }}</div>
    </div>
    <el-input v-model="prompt" type="textarea" :rows="2" placeholder="Ask AI..." />
    <el-button class="mt8" type="primary" @click="send" block>发送</el-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useChatStore } from '../store/chat'

const props = defineProps({ context: Array })
const chat = useChatStore()
const prompt = ref('')

const send = async () => {
  if (!prompt.value) return
  await chat.ask(prompt.value, props.context || [])
  prompt.value = ''
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 100%;
}
.history {
  flex: 1;
  overflow: auto;
  padding: 4px;
  border: 1px solid #eee;
  border-radius: 6px;
}
.user {
  color: #1a73e8;
  margin: 4px 0;
}
.assistant {
  color: #166534;
  margin: 4px 0;
}
.mt8 {
  margin-top: 8px;
}
</style>





