<script setup lang="ts">
const currentPage = defineModel<number>('currentPage', { required: true })
const pageSize = defineModel<number>('pageSize', { required: true })

defineProps<{
  total: number
  pageStart: number
  pageEnd: number
}>()

const emit = defineEmits<{
  'page-change': [page: number]
  'size-change': [size: number]
}>()

function onPageChange(page: number) {
  currentPage.value = page
  emit('page-change', page)
}

function onSizeChange(size: number) {
  pageSize.value = size
  emit('size-change', size)
}
</script>

<template>
  <div v-if="total > 0" class="admin-pagination-footer">
    <span class="footer-summary">
      显示第 {{ pageStart }}–{{ pageEnd }} 条，共 {{ total }} 条
    </span>
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="sizes, prev, pager, next, jumper"
      background
      @current-change="onPageChange"
      @size-change="onSizeChange"
    />
  </div>
</template>

<style scoped>
.admin-pagination-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.6);
  border-top: 1px solid rgba(99, 102, 241, 0.08);
}

.footer-summary {
  font-size: 13px;
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .admin-pagination-footer {
    flex-direction: column;
    align-items: flex-end;
  }
}
</style>
