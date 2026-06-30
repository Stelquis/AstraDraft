<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import axios from 'axios'

const API = 'http://localhost:8000'

interface Drawing {
  id: string
  filename: string
  file_size: number
  status: string
  param_count: number
  created_at: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const drawings = ref<Drawing[]>([])
const currentId = ref<string | null>(null)
const currentDrawing = ref<Drawing | null>(null)
const messages = ref<Message[]>([])
const question = ref('')
const loading = ref(false)
const msgContainer = ref<HTMLElement | null>(null)

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API}/drawings`)
    drawings.value = data.drawings
    if (drawings.value.length > 0) {
      selectDrawing(drawings.value[0].id)
    }
  } catch (e) {
    console.error('Failed to load drawings:', e)
  }
})

function onUploadSuccess(ctx: any) {
  const res = ctx?.response
  if (res?.drawing_id) {
    loadDrawings().then(() => selectDrawing(res.drawing_id))
  }
}

async function loadDrawings() {
  try {
    const { data } = await axios.get(`${API}/drawings`)
    drawings.value = data.drawings
  } catch (e) {
    console.error(e)
  }
}

async function selectDrawing(id: string) {
  currentId.value = id
  try {
    const { data } = await axios.get(`${API}/drawings/${id}`)
    currentDrawing.value = data
    const { data: hist } = await axios.get(`${API}/drawings/${id}/history`)
    messages.value = hist.history.length > 0
      ? hist.history.reverse().map((h: any) => [
          { role: 'user' as const, content: h.question },
          { role: 'assistant' as const, content: h.answer },
        ]).flat()
      : [{ role: 'assistant' as const, content: `图纸「${data.filename}」已加载，共 ${data.param_count} 个参数。请问你想了解什么？` }]
  } catch (e) {
    console.error(e)
  }
}

async function ask() {
  const q = question.value.trim()
  if (!q || !currentId.value || loading.value) return
  loading.value = true
  messages.value.push({ role: 'user', content: q })
  question.value = ''
  await nextTick()
  scrollToBottom()

  try {
    const { data } = await axios.post(`${API}/drawings/${currentId.value}/query`, {
      question: q,
      session_id: sessionId(),
    })
    messages.value.push({ role: 'assistant', content: data.answer })
  } catch (e: any) {
    messages.value.push({ role: 'assistant', content: '查询失败：' + (e.response?.data?.detail || e.message) })
  }
  loading.value = false
  await nextTick()
  scrollToBottom()
}

function scrollToBottom() {
  msgContainer.value?.scrollTo({ top: msgContainer.value.scrollHeight, behavior: 'smooth' })
}

function sessionId(): string {
  let sid = localStorage.getItem('draft_session')
  if (!sid) {
    sid = Math.random().toString(36).slice(2, 10)
    localStorage.setItem('draft_session', sid)
  }
  return sid
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatTime(ts: string): string {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="app-layout">
    <!-- 左侧：图纸列表 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>DeepAstraDraft</h2>
        <span class="version">v1.0</span>
      </div>
      <div class="upload-area">
        <t-upload
          theme="file"
          accept=".dwg,.dxf"
          :action="`${API}/upload`"
          :show-upload-progress="true"
          @success="onUploadSuccess"
          :auto-upload="true"
        >
          <t-button block theme="primary" size="large">
            <template #icon><t-icon name="upload" /></template>
            上传图纸
          </t-button>
        </t-upload>
        <p class="upload-hint">支持 DWG / DXF 格式</p>
      </div>
      <nav class="drawing-list">
        <div
          v-for="d in drawings"
          :key="d.id"
          :class="['drawing-item', { active: currentId === d.id }]"
          @click="selectDrawing(d.id)"
        >
          <div class="drawing-name">{{ d.filename }}</div>
          <div class="drawing-meta">
            <t-tag size="small" theme="success" variant="light">{{ d.param_count }} 参数</t-tag>
            <span class="drawing-time">{{ formatTime(d.created_at) }}</span>
          </div>
        </div>
        <div v-if="drawings.length === 0" class="empty-list">
          <t-icon name="file-paste" size="32px" />
          <p>暂无图纸，上传一张开始吧</p>
        </div>
      </nav>
    </aside>

    <!-- 右侧：对话区 -->
    <main class="chat-area" v-if="currentDrawing">
      <header class="chat-header">
        <div class="chat-title">
          <t-icon name="file-paste" size="20px" />
          <h3>{{ currentDrawing.filename }}</h3>
          <t-tag theme="primary" variant="light">{{ currentDrawing.param_count }} 参数</t-tag>
        </div>
      </header>

      <div class="messages" ref="msgContainer">
        <div
          v-for="(msg, i) in messages"
          :key="i"
          :class="['message', msg.role]"
        >
          <div class="avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="bubble">{{ msg.content }}</div>
        </div>
        <div v-if="loading" class="message assistant">
          <div class="avatar">🤖</div>
          <div class="bubble typing">思考中...</div>
        </div>
      </div>

      <div class="input-area">
        <t-input
          v-model="question"
          placeholder="请输入技术参数问题，如：总长度是多少、材质是什么..."
          size="large"
          clearable
          @keyup.enter="ask"
        />
        <t-button theme="primary" size="large" @click="ask" :loading="loading">发送</t-button>
      </div>
    </main>

    <!-- 空状态 -->
    <main class="chat-area empty" v-else>
      <t-icon name="file-paste" size="64px" style="color: #ccc" />
      <h3>请选择或上传一张 CAD 图纸</h3>
      <p>上传后自动解析参数，即可开始问答</p>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background: #f5f6f8;
}

/* ---- 侧边栏 ---- */
.sidebar {
  width: 280px;
  background: #fff;
  border-right: 1px solid #e7e8ea;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-header {
  padding: 20px 16px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sidebar-header h2 {
  font-size: 18px;
  font-weight: 700;
  color: #0052d9;
}
.version {
  font-size: 12px;
  color: #999;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
}
.upload-area {
  padding: 0 16px 12px;
}
.upload-hint {
  font-size: 12px;
  color: #999;
  margin-top: 6px;
  text-align: center;
}
.drawing-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}
.drawing-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background .15s;
}
.drawing-item:hover { background: #f3f4f6; }
.drawing-item.active { background: #e8f0fe; }
.drawing-name {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.drawing-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}
.drawing-time {
  font-size: 11px;
  color: #aaa;
}
.empty-list {
  text-align: center;
  padding: 40px 16px;
  color: #bbb;
  font-size: 13px;
}

/* ---- 对话区 ---- */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-area.empty {
  justify-content: center;
  align-items: center;
  gap: 12px;
  color: #999;
}
.chat-header {
  padding: 14px 24px;
  background: #fff;
  border-bottom: 1px solid #e7e8ea;
}
.chat-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chat-title h3 {
  font-size: 16px;
  font-weight: 600;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}
.message {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
  max-width: 85%;
}
.message.user { flex-direction: row-reverse; margin-left: auto; }
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: #f0f0f0;
  flex-shrink: 0;
}
.message.user .avatar { background: #0052d9; color: #fff; }
.bubble {
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.message.assistant .bubble { background: #fff; border: 1px solid #e7e8ea; }
.message.user .bubble { background: #0052d9; color: #fff; }
.typing { color: #999; font-style: italic; }

.input-area {
  padding: 14px 24px;
  background: #fff;
  border-top: 1px solid #e7e8ea;
  display: flex;
  gap: 10px;
}
.input-area :deep(.t-input) { flex: 1; }
</style>
