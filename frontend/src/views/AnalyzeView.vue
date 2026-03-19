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

    <!-- System Verdict Hero Section -->
    <div v-if="scoring" class="mb-6 rounded-xl p-6 border-2" :class="verdictClasses">
      <div class="flex items-center gap-4">
        <!-- Verdict Icon -->
        <div class="w-16 h-16 rounded-full flex items-center justify-center" :class="verdictIconClasses">
          <span class="text-3xl">{{ verdictIcon }}</span>
        </div>
        
        <!-- Verdict Text -->
        <div class="flex-1">
          <h2 class="text-xl font-bold" :class="verdictTextClasses">ВЕРДИКТ: {{ scoring.decision }}</h2>
          <p class="text-sm opacity-80 mt-1">{{ scoring.reasoning }}</p>
        </div>
        
        <!-- Total Score -->
        <div class="text-right">
          <div class="text-4xl font-bold">{{ scoring.total_score }}</div>
          <div class="text-xs uppercase tracking-wide opacity-70">из 100</div>
        </div>
      </div>
      
      <!-- Score Progress Bar -->
      <div class="mt-4">
        <div class="h-3 bg-black/10 rounded-full overflow-hidden">
          <div 
            class="h-full rounded-full transition-all duration-500" 
            :class="verdictBarClasses"
            :style="{ width: scoring.total_score + '%' }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Score Breakdown -->
    <div v-if="scoring" class="grid grid-cols-3 gap-4 mb-6">
      <!-- Budget Score -->
      <div class="card text-center">
        <div class="text-2xl font-bold text-emerald-600">{{ scoring.budget_score }}</div>
        <div class="text-xs text-slate-500 uppercase tracking-wide">Бюджет</div>
        <div class="text-xs text-slate-400">/ 40</div>
        <div class="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div class="h-full bg-emerald-500 rounded-full" :style="{ width: (scoring.budget_score / 40 * 100) + '%' }"></div>
        </div>
      </div>
      
      <!-- Complexity Score -->
      <div class="card text-center">
        <div class="text-2xl font-bold text-blue-600">{{ scoring.complexity_score }}</div>
        <div class="text-xs text-slate-500 uppercase tracking-wide">Сложность</div>
        <div class="text-xs text-slate-400">/ 30</div>
        <div class="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div class="h-full bg-blue-500 rounded-full" :style="{ width: (scoring.complexity_score / 30 * 100) + '%' }"></div>
        </div>
      </div>
      
      <!-- Competition Score -->
      <div class="card text-center">
        <div class="text-2xl font-bold text-purple-600">{{ scoring.competition_score }}</div>
        <div class="text-xs text-slate-500 uppercase tracking-wide">Конкуренция</div>
        <div class="text-xs text-slate-400">/ 30</div>
        <div class="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div class="h-full bg-purple-500 rounded-full" :style="{ width: (scoring.competition_score / 30 * 100) + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- Action buttons -->
    <div class="flex gap-3 mb-6">
      <button
        class="btn-primary flex-1 justify-center py-3 text-base"
        :disabled="!ready || loading"
        @click="analyze"
      >
        <svg v-if="loading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span>{{ loading ? 'Анализируем документ...' : '📋 Запустить полный анализ' }}</span>
      </button>
      
      <button
        v-if="ready && !scoring"
        class="btn-secondary justify-center py-3 text-base px-6"
        :disabled="loading"
        @click="analyzeWithScoring"
      >
        <span>🎯 Анализ с вердиктом</span>
      </button>
    </div>

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
import { ref, computed, inject } from 'vue'
import { RouterLink } from 'vue-router'
import { marked } from 'marked'
import { useSSE } from '../composables/useSSE'

const ready = inject('appReady')
const { text, loading, error, stream, reset } = useSSE()

// Scoring data
const scoring = ref(null)

// Compute verdict styles
const verdictClasses = computed(() => {
  if (!scoring.value) return 'border-slate-200 bg-slate-50'
  switch (scoring.value.decision) {
    case 'GO': return 'border-emerald-500 bg-emerald-50'
    case 'REVIEW': return 'border-amber-500 bg-amber-50'
    case 'REJECT': return 'border-red-500 bg-red-50'
    default: return 'border-slate-200 bg-slate-50'
  }
})

const verdictIconClasses = computed(() => {
  if (!scoring.value) return 'bg-slate-200'
  switch (scoring.value.decision) {
    case 'GO': return 'bg-emerald-500 text-white'
    case 'REVIEW': return 'bg-amber-500 text-white'
    case 'REJECT': return 'bg-red-500 text-white'
    default: return 'bg-slate-200'
  }
})

const verdictTextClasses = computed(() => {
  if (!scoring.value) return 'text-slate-600'
  switch (scoring.value.decision) {
    case 'GO': return 'text-emerald-700'
    case 'REVIEW': return 'text-amber-700'
    case 'REJECT': return 'text-red-700'
    default: return 'text-slate-600'
  }
})

const verdictBarClasses = computed(() => {
  if (!scoring.value) return 'bg-slate-400'
  switch (scoring.value.decision) {
    case 'GO': return 'bg-emerald-500'
    case 'REVIEW': return 'bg-amber-500'
    case 'REJECT': return 'bg-red-500'
    default: return 'bg-slate-400'
  }
})

const verdictIcon = computed(() => {
  if (!scoring.value) return '?'
  switch (scoring.value.decision) {
    case 'GO': return '✓'
    case 'REVIEW': return '!'
    case 'REJECT': return '✕'
    default: return '?'
  }
})

function renderMarkdown(t) {
  return marked(t || '', { breaks: true })
}

async function analyze() {
  reset()
  scoring.value = null
  await stream('/api/analyze')
}

async function analyzeWithScoring() {
  reset()
  scoring.value = null
  try {
    const response = await fetch('/api/analyze-with-scoring', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    const data = await response.json()
    console.log('Scoring response:', data)
    // Data is returned directly, not wrapped in scoring object
    if (data.total_score !== undefined) {
      scoring.value = data
    } else if (data.scoring) {
      scoring.value = data.scoring
    }
  } catch (e) {
    console.error('Error analyzing with scoring:', e)
  }
}
</script>
