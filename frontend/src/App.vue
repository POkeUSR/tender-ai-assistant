<template>
  <div class="flex h-screen overflow-hidden bg-slate-50">
    <!-- Sidebar -->
    <aside class="w-64 bg-sidebar flex flex-col flex-shrink-0">
      <!-- Logo -->
      <div class="flex items-center gap-3 px-6 py-5 border-b border-slate-700">
        <div class="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div>
          <div class="text-white font-semibold text-sm leading-tight">Tender AI</div>
          <div class="text-slate-400 text-xs">Assistant</div>
        </div>
      </div>

      <!-- Status badge -->
      <div class="px-4 py-3 border-b border-slate-700">
        <div class="flex items-center gap-2 px-3 py-2 rounded-lg" :class="ready ? 'bg-emerald-900/40' : 'bg-slate-700/50'">
          <div class="w-2 h-2 rounded-full flex-shrink-0" :class="ready ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'"></div>
          <span class="text-xs truncate" :class="ready ? 'text-emerald-300' : 'text-slate-400'">
            {{ ready ? filename : 'Документ не загружен' }}
          </span>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-3 py-4 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-300 hover:text-white hover:bg-sidebar-hover transition-colors duration-150 group"
          active-class="bg-accent/20 text-white"
        >
          <span class="text-lg">{{ item.icon }}</span>
          <div>
            <div class="text-sm font-medium">{{ item.label }}</div>
            <div class="text-xs text-slate-500 group-hover:text-slate-400">{{ item.desc }}</div>
          </div>
        </RouterLink>
      </nav>

      <!-- Footer -->
      <div class="px-4 py-4 border-t border-slate-700">
        <div class="text-xs text-slate-500 text-center">Powered by GPT-4o-mini</div>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-auto">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { getStatus } from './api'

const ready = ref(false)
const filename = ref('')

const navItems = [
  { path: '/upload', icon: '📤', label: 'Загрузка', desc: 'Загрузить PDF тендера' },
  { path: '/chat', icon: '💬', label: 'Чат', desc: 'Вопросы по тендеру' },
  { path: '/analyze', icon: '📋', label: 'Анализ', desc: 'Полный анализ тендера' },
  { path: '/risks', icon: '⚠️', label: 'Риски', desc: 'Оценка рисков участия' },
]

async function checkStatus() {
  try {
    const data = await getStatus()
    ready.value = data.ready
    filename.value = data.filename || ''
  } catch {
    // backend offline
  }
}

function refreshStatus() {
  checkStatus()
}

provide('refreshStatus', refreshStatus)
provide('appReady', ready)
provide('appFilename', filename)

onMounted(checkStatus)
</script>
