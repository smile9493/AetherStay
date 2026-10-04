<script setup lang="ts">
import { RouterView } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
</script>

<template>
  <!-- 全局中文语言包：日期选择器、弹窗按钮等内置文案随之中文化 -->
  <el-config-provider :locale="zhCn">
    <RouterView />
  </el-config-provider>
</template>
