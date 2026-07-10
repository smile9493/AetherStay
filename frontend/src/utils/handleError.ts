import { ElMessage } from 'element-plus'
import axios from 'axios'

/**
 * Unified API error handler for Element Plus UI feedback.
 * Extracts backend detail field, falls back to generic message, and logs to console.
 */
export function handleApiError(err: unknown, fallback = '操作失败，请稍后重试') {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') {
      ElMessage.error(detail)
    } else {
      ElMessage.error(fallback)
    }
  } else {
    ElMessage.error(fallback)
  }
  console.error('[API Error]', err)
}
