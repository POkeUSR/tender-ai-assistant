<template>
  <div class="p-8 max-w-2xl mx-auto">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-slate-800">Загрузка документов</h1>
      <p class="text-slate-500 mt-1">Загрузите один или несколько файлов тендерной документации (PDF, DOCX, TXT)</p>
    </div>

    <!-- Drop Zone -->
    <div
      class="border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 cursor-pointer"
      :class="isDragging ? 'border-accent bg-blue-50' : 'border-slate-300 hover:border-accent hover:bg-slate-50'"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="handleDrop"
      @click="fileInput.click()"
    >
      <div class="flex flex-col items-center gap-4">
        <div class="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center">
          <svg class="w-8 h-8 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <div>
          <p class="text-slate-700 font-medium">Перетащите файлы сюда</p>
          <p class="text-slate-400 text-sm mt-1">или нажмите для выбора файлов</p>
        </div>
        <span class="text-xs text-slate-400 bg-slate-100 px-3 py-1 rounded-full">PDF, DOCX, TXT · Можно несколько файлов</span>
      </div>
      <input ref="fileInput" type="file" accept=".pdf,.docx,.doc,.txt" multiple class="hidden" @change="handleSelect" />
    </div>

    <!-- Selected files list -->
    <div v-if="selectedFiles.length" class="mt-4 flex flex-col gap-2">
      <div
        v-for="(file, i) in selectedFiles"
        :key="i"
        class="card flex items-center gap-4"
      >
        <div class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          :class="fileIconClass(file.name)">
          <svg class="w-6 h-6" :class="fileIconColor(file.name)" fill="currentColor" viewBox="0 0 20 20">
            <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-medium text-slate-800 truncate">{{ file.name }}</p>
          <p class="text-sm text-slate-400">{{ formatSize(file.size) }} · {{ fileExt(file.name).toUpperCase() }}</p>
        </div>
        <button class="text-slate-400 hover:text-slate-600" @click.stop="removeFile(i)">✕</button>
      </div>
    </div>

    <!-- Upload button -->
    <button
      class="btn-primary mt-6 w-full justify-center py-3 text-base"
      :disabled="!selectedFiles.length || uploading"
      @click="upload"
    >
      <svg v-if="uploading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      <span>{{ uploading ? 'Обрабатываем...' : `Загрузить и проиндексировать (${selectedFiles.length})` }}</span>
    </button>

    <!-- Result -->
    <div v-if="result" class="mt-6 card" :class="result.error ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'">
      <div class="flex items-center gap-3">
        <span class="text-2xl">{{ result.error ? '❌' : '✅' }}</span>
        <div>
          <p class="font-semibold" :class="result.error ? 'text-red-700' : 'text-emerald-700'">
            {{ result.error ? 'Ошибка загрузки' : 'Документы проиндексированы!' }}
          </p>
          <p class="text-sm mt-0.5" :class="result.error ? 'text-red-600' : 'text-emerald-600'">
            {{ result.error || `${(result.filenames || [result.filename]).join(', ')} · ${result.chunks_count} фрагментов` }}
          </p>
        </div>
      </div>
      <div v-if="!result.error" class="mt-4 flex gap-3">
        <RouterLink to="/chat" class="btn-primary text-sm">Перейти в чат →</RouterLink>
        <RouterLink to="/analyze" class="btn-secondary text-sm">Анализ тендера</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { RouterLink } from 'vue-router'
import { uploadFiles } from '../api'

const refreshStatus = inject('refreshStatus')

const fileInput = ref(null)
const selectedFiles = ref([])
const uploading = ref(false)
const isDragging = ref(false)
const result = ref(null)

const ALLOWED_EXTS = ['.pdf', '.docx', '.doc', '.txt']

function fileExt(name) {
  return name.slice(name.lastIndexOf('.')).toLowerCase()
}

function isAllowed(file) {
  return ALLOWED_EXTS.includes(fileExt(file.name))
}

function fileIconClass(name) {
  const ext = fileExt(name)
  if (ext === '.pdf') return 'bg-red-100'
  if (ext === '.docx' || ext === '.doc') return 'bg-blue-100'
  return 'bg-slate-100'
}

function fileIconColor(name) {
  const ext = fileExt(name)
  if (ext === '.pdf') return 'text-red-500'
  if (ext === '.docx' || ext === '.doc') return 'text-blue-500'
  return 'text-slate-500'
}

function addFiles(files) {
  for (const file of files) {
    if (isAllowed(file) && !selectedFiles.value.find(f => f.name === file.name)) {
      selectedFiles.value.push(file)
    }
  }
}

function handleDrop(e) {
  isDragging.value = false
  addFiles(Array.from(e.dataTransfer.files))
}

function handleSelect(e) {
  addFiles(Array.from(e.target.files))
  e.target.value = ''
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

async function upload() {
  if (!selectedFiles.value.length) return
  uploading.value = true
  result.value = null
  try {
    const data = await uploadFiles(selectedFiles.value)
    result.value = data
    refreshStatus()
  } catch (e) {
    result.value = { error: e.message }
  } finally {
    uploading.value = false
  }
}
</script>
