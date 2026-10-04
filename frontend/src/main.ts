import { createApp } from 'vue'
import { createPinia } from 'pinia'
import {
  ChatDotRound,
  CircleCheck,
  DataLine,
  House,
  Loading,
  Lock,
  MagicStick,
  Timer,
} from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

// 图标不参与组件自动导入，仅按需注册模板中实际用到的（含 :is 字符串绑定的动态图标）
const icons = {
  ChatDotRound,
  CircleCheck,
  DataLine,
  House,
  Loading,
  Lock,
  MagicStick,
  Timer,
}

for (const [name, component] of Object.entries(icons)) {
  app.component(name, component)
}

app.use(createPinia())
app.use(router)
app.mount('#app')