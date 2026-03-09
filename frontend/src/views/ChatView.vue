<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="px-6 py-4 border-b border-slate-200 bg-white flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-slate-800">Чат с тендером</h1>
        <p class="text-sm text-slate-400">Задавайте вопросы по документации</p>
      </div>
      <button v-if="messages.length" class="btn-secondary text-sm" @click="clearChat">Очистить</button>
    </div>

    <!-- Messages -->
    <div ref="messagesEl" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      <!-- Empty state -->
      <div v-if="!messages.length" class="flex flex-col items-center justify-center h-full gap-4 text-center">
        <div class="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center">
          <span class="text-3xl">💬</span>
        </div>
        <div>
          <p class="font-semibold text-slate-700">Готов отвечать на вопросы</p>
          <p class="text-sm text-slate-400 mt-1">Спросите о сроках, требованиях, стоимости...</p>
        </div>
        <div class="grid grid-cols-2 gap-2 mt-2 max-w-md w-full">
          <button
            v-for="q in suggestions"
            :key="q"
            class="text-left text-sm bg-white border border-slate-200 rounded-lg px-3 py-2 hover:border-accent hover:bg-blue-50 transition-colors"
            @click="sendSuggestion(q)"
          >{{ q }}</button>
        </div>
      </div>

      <!-- Message bubbles -->
      <template v-else>
        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="flex gap-3"
          :class="msg.role === 'user' ? 'flex-row-reverse' : ''"
        >
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm"
            :class="msg.role === 'user' ? 'bg-accent text-white' : 'bg-slate-200 text-slate-600'"
          >
            {{ msg.role === 'user' ? '👤' : '🤖' }}
          </div>
          <div
            class="max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
            :class="msg.role === 'user'
              ? 'bg-accent text-white rounded-tr-sm'
              : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm'"
          >
            <div
              v-if="msg.role === 'assistant'"
              class="prose prose-sm max-w-none prose-headings:text-slate-800"
              :class="{ 'streaming-cursor': msg.streaming }"
              v-html="renderMarkdown(msg.content)"
            ></div>
            <span v-else>{{ msg.content }}</span>
          </div>
        </div>
      </template>
    </div>

    <!-- No document warning -->
    <div v-if="!ready" class="mx-6 mb-3 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-sm text-amber-700">
      <span>⚠️</span>
      <span>Сначала <RouterLink to="/upload" class="underline font-medium">загрузите тендерный документ</RouterLink></span>
    </div>

    <!-- Input bar -->
    <div class="px-6 pb-6 pt-2">
      <div class="flex gap-3 bg-white border border-slate-200 rounded-xl p-2 shadow-sm focus-within:border-accent focus-within:ring-1 focus-within:ring-accent">
        <textarea
          v-model="question"
          rows="1"
          class="flex-1 resize-none outline-none text-sm py-2 px-2 text-slate-800 placeholder-slate-400"
          placeholder="Введите вопрос по тендеру..."
          :disabled="loading || !ready"
          @keydown.enter.exact.prevent="send"
          @input="autoResize"
        ></textarea>
        <button
          class="btn-primary px-4 self-end rounded-lg"
          :disabled="!question.trim() || loading || !ready"
          @click="send"
        >
          <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
      <p class="text-xs text-slate-400 mt-2 text-center">Enter для отправки · Shift+Enter для новой строки</p>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, nextTick } from 'vue'
import { RouterLink } from 'vue-router'
import { marked } from 'marked'
import { useSSE } from '../composables/useSSE'

const ready = inject('appReady')
const { loading, error, stream } = useSSE()

const question = ref('')
const messages = ref([])
const messagesEl = ref(null)

const suggestions = [
  'Каков предмет закупки?',
  'Какие сроки подачи заявки?',
  'Какие документы нужны?',
  'Какова начальная цена контракта?',
]

function renderMarkdown(text) {
  return marked(text || '', { breaks: true })
}

function clearChat() {
  messages.value = []
}

function sendSuggestion(q) {
  question.value = q
  send()
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

async function send() {
  const q = question.value.trim()
  if (!q || loading.value || !ready.value) return

  messages.value.push({ role: 'user', content: q })
  question.value = ''
  await scrollToBottom()

  const aiMsg = { role: 'assistant', content: '', streaming: true }
  messages.value.push(aiMsg)

  const idx = messages.value.length - 1

  // Manual stream (can't use composable text directly due to per-message tracking)
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q }),
    })

    if (!response.ok) {
      const err = await response.json()
      messages.value[idx].content = `❌ Ошибка: ${err.detail}`
      messages.value[idx].streaming = false
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const raw = decoder.decode(value, { stream: true })
      for (const line of raw.split('\n')) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (data === '[DONE]') break
          try {
            const parsed = JSON.parse(data)
            if (parsed.token) {
              messages.value[idx].content += parsed.token
              await scrollToBottom()
            }
          } catch { /* skip */ }
        }
      }
    }
  } catch (e) {
    messages.value[idx].content = `❌ ${e.message}`
  } finally {
    messages.value[idx].streaming = false
  }
}
</script>
