import { ref, computed } from 'vue'

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export function usePagination(defaultPageSize = 20) {
  const currentPage = ref(1)
  const pageSize = ref(defaultPageSize)
  const total = ref(0)

  const pageStart = computed(() =>
    total.value === 0 ? 0 : (currentPage.value - 1) * pageSize.value + 1,
  )
  const pageEnd = computed(() =>
    Math.min(currentPage.value * pageSize.value, total.value),
  )

  function resetPage() {
    currentPage.value = 1
  }

  function applyPageResult(result: PaginatedResult<unknown>) {
    total.value = result.total
    currentPage.value = result.page
    pageSize.value = result.page_size
  }

  return {
    currentPage,
    pageSize,
    total,
    pageStart,
    pageEnd,
    resetPage,
    applyPageResult,
  }
}
