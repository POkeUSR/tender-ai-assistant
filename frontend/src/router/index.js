import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import ChatView from '../views/ChatView.vue'
import AnalyzeView from '../views/AnalyzeView.vue'
import RisksView from '../views/RisksView.vue'

const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/upload', component: UploadView, meta: { title: 'Загрузка документа' } },
  { path: '/chat', component: ChatView, meta: { title: 'Чат с тендером' } },
  { path: '/analyze', component: AnalyzeView, meta: { title: 'Анализ тендера' } },
  { path: '/risks', component: RisksView, meta: { title: 'Анализ рисков' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
