<template>
  <div class="p-8 max-w-3xl mx-auto">
    <div class="mb-8 flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">Полный анализ тендера</h1>
        <p class="text-slate-500 mt-1">8-точечный структурированный анализ документации</p>
      </div>
    </div>

    <!-- No document warning -->
    <div v-if="!ready" class="card border-amber-200 bg-amber-50 mb-6 flex items-center gap-3">
      <span class="text-2xl">⚠️</span>
      <div>
        <p class="font-semibold text-amber-800">Документ не загружен</p>
        <p class="text-sm text-amber-600">
          <RouterLink to="/upload" class="underline">Загрузите тендерную документацию</RouterLink> для начала анализа
        </p>
      </div>
    </div>

    <!-- Action button -->
    <button
      class="btn-primary w-full justify-center py-3 text-base mb-6"
      :disabled="!ready || loading"
      @click="analyze"
    >
      <svg v-if="loading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      <span>{{ loading ? 'Анализируем документ...' : '📋 Запустить полный анализ' }}</span>
    </button>

    <!-- Progress indicator -->
    <div v-if="loading" class="mb-4 h-1.5 bg-slate-200 rounded-full overflow-hidden">
      <div class="h-full bg-accent rounded-full animate-pulse" style="width: 100%"></div>
    </div>

    <!-- Result -->
    <div v-if="text" class="card">
      <div class="flex items-center gap-2 mb-4 pb-4 border-b border-slate-100">
        <span class="text-xl">📋</span>
        <h2 class="font-semibold text-slate-700">Результат анализа</h2>
        <span v-if="loading" class="ml-auto text-xs text-accent animate-pulse font-medium">● Генерация...</span>
      </div>
      <div
        class="prose prose-sm max-w-none prose-headings:text-slate-800 prose-strong:text-slate-800"
        :class="{ 'streaming-cursor': loading }"
        v-html="renderMarkdown(text)"
      ></div>
    </div>

    <!-- Error -->
    <div v-if="error" class="card border-red-200 bg-red-50">
      <p class="text-red-700 font-medium">❌ {{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { RouterLink } from 'vue-router'
import { marked } from 'marked'
import { useSSE } from '../composables/useSSE'

const ready = inject('appReady')
const { text, loading, error, stream, reset } = useSSE()

function renderMarkdown(t) {
  return marked(t || '', { breaks: true })
}

async function analyze() {
  reset()
  await stream('/api/analyze')
}
</script>
